"""Convert the preserved Kingroon INI into a native alpha12 offline repository."""

from __future__ import annotations

import argparse
import configparser
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import uuid
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = "kingroon-fff"
VENDOR = "Kingroon"
VERSION = "3.0.0-alpha1"
SOURCE = ROOT / "legacy/1.4.2/Kingroon.ini"
SCHEMA = ROOT / "schema/3.0.0-alpha12.json"
NAMESPACE = uuid.UUID("01895621-e18c-4eb6-8131-827d83c8c3c1")
MODELS = ("KP3S", "KP3SBLTOUCH", "KP3SProS1", "KP3SProS1BLTOUCH")
NOZZLES = ("0.2", "0.3", "0.4", "0.5", "0.6")

# These are metadata, removed options or project-level placement settings.
# Every omission is included, with its original value, in migration-report.json.
OMIT = {
    "inherits", "compatible_printers", "compatible_printers_condition",
    "renamed_from", "filament_settings_id", "print_settings_id", "printer_settings_id",
    "nozzle_diameter", "default_print_profile", "default_filament_profile",
    "extruder_colour", "clip_multipart_objects", "infill_only_where_needed",
    "top_fan_speed", "wipe_tower_rotation_angle", "wipe_tower_x", "wipe_tower_y",
}
RENAMES = {"external_fill_pattern": "top_fill_pattern"}


def stable_id(kind, name):
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{name}"))


def read_source():
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.read(SOURCE, encoding="utf-8-sig")
    return config


def resolve(config, kind, name, stack=()):
    # The upstream AmazonBasics TPU preset references an absent *FLEX* node.
    # The bundle's existing TPU base is *TPU*. Keep the source unchanged.
    if kind == "filament" and name == "*FLEX*" and "filament:*FLEX*" not in config:
        name = "*TPU*"
    section = f"{kind}:{name}"
    if section in stack:
        raise ValueError(f"Inheritance cycle: {stack + (section,)}")
    result = {}
    for parent in config[section].get("inherits", "").split(";"):
        if parent.strip():
            result.update(resolve(config, kind, parent.strip(), stack + (section,)))
    result.update(dict(config[section]))
    return result


def unquote(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1]
    return raw


def value(raw, spec):
    kind = spec["type"]
    if raw == "nil":
        return None
    if kind == "Array":
        separator = ";" if spec["element_type"] == "String" else ","
        return [value(v.strip(), {**spec, "type": spec["element_type"]})
                for v in raw.split(separator)] if raw else []
    if kind == "Vec2d":
        # Native YAML accepts the same x-separated vector representation.
        return raw
    if kind == "String":
        return unquote(raw).replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
    if kind == "Bool":
        if raw not in ("0", "1"):
            raise ValueError(f"Invalid boolean: {raw}")
        return raw == "1"
    if kind in ("Int", "OptInt"):
        return int(raw)
    if kind == "Float":
        return float(raw)
    if kind in ("FloatOrPercentage", "Percentage"):
        return raw if raw.endswith("%") else float(raw)
    if kind == "Enum":
        if raw not in spec["enum_values"]:
            raise ValueError(f"Unknown enum value {raw!r}; expected {spec['enum_values']}")
        return raw
    raise ValueError(f"Unsupported schema type {kind}")


def migrate_condition(raw):
    return raw.replace("printer_model", "printer.model").replace("nozzle_diameter[0]", "tool.nozzle_diameter")


def convert(config):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    specs = {x["name"]: x for kind in ("printer", "print", "filament")
             for x in schema[kind]["items"]}
    printer_keys = {x["name"] for x in schema["printer"]["items"]}
    print_keys = {x["name"] for x in schema["print"]["items"]}
    tool_keys = {x["name"] for x in schema["tool_print"]["overrides"]}
    filament_keys = {x["name"] for group in ("items", "overrides") for x in schema["filament"][group]}
    report = {"source_version": config["vendor"]["config_version"],
              "target": "PrusaSlicer 3.0.0-alpha12", "omitted": {}, "renamed": RENAMES,
              "validation": "Generated; see VALIDATION.md for executable checks."}
    report["repairs"] = {"AmazonBasics TPU @KINGROON": "Missing *FLEX* parent resolved to existing *TPU* base"}

    def mapped(raw, allowed, label):
        output = {}
        for key, text in raw.items():
            if key == "printer_model" or key == "printer_variant":
                continue
            if key in OMIT:
                report["omitted"].setdefault(key, set()).add(text)
                continue
            dest = RENAMES.get(key, key)
            if key.startswith("filament_") and key[len("filament_"):] in tool_keys:
                dest = key[len("filament_"):]
            if dest not in specs:
                raise ValueError(f"Unmapped setting {label}: {key}={text}")
            if dest not in allowed:
                continue  # explicitly routed to another preset category
            if dest == "gcode_label_objects" and text in ("0", "1"):
                text = {"0": "disabled", "1": "octoprint"}[text]
            if dest == "ensure_vertical_shell_thickness" and text in ("0", "1"):
                text = {"0": "disabled", "1": "enabled"}[text]
            if dest == "support_material" and text in ("0", "1"):
                text = {"0": "none", "1": "everywhere"}[text]
            output[dest] = value(text, specs[dest])
        return output

    vendor = [{"kind": "vendor", "id": VENDOR, "name": "Kingroon", "version": VERSION,
               "features": {"printer": {}, "tool": {"nozzle_diameter": {"default": 0.4}}},
               "printer_families": [{"label": "Kingroon", "base_model": "KINGROON",
                                     "printer_configs_order": [f"{model}-{nozzle}" for model in MODELS for nozzle in NOZZLES]}]}]
    for model in MODELS:
        info = config[f"printer_model:{model}"]
        visual = {key: info[key] for key in ("bed_model", "bed_texture") if info.get(key)}
        if (ROOT / VENDOR / f"{model.lower()}_thumbnail.png").exists():
            visual["thumbnail"] = f"{model.lower()}_thumbnail.png"
        vendor.append({"kind": "printer", "id": model, "name": info["name"],
                       "technology": "FFF", "model": {"base_model": "KINGROON", "model": model},
                       "tool_count": 1, "visual": visual})
        for nozzle in NOZZLES:
            vendor.append({"kind": "printer_config", "id": f"{model}-{nozzle}", "name": info["name"],
                           "printer": model, "legacy_printer_model": [model], "tool_count": 1,
                           "tools": [{"tool": nozzle}], "sheet": "stock"})
    for nozzle in NOZZLES:
        vendor.append({"kind": "tool", "id": nozzle, "name": f"{nozzle} mm",
                       "technology": "FFF", "features": {"nozzle_diameter": {"default": float(nozzle)}}})
    vendor.append({"kind": "sheet", "id": "stock", "name": "Stock build plate", "type": "stock"})

    public = {kind: [section.split(":", 1)[1] for section in config.sections()
                    if section.startswith(kind + ":") and not section.split(":", 1)[1].startswith("*")]
              for kind in ("printer", "print", "filament")}
    resolved_printers = [resolve(config, "printer", name) for name in public["printer"]]
    # 3.0 moved clearance settings from Print to Printer. All source print
    # presets must agree before a value can be moved to a shared printer node.
    relocated = {}
    for name in public["print"]:
        for key, text in resolve(config, "print", name).items():
            if key in printer_keys:
                if key in relocated and relocated[key] != text:
                    raise ValueError(f"Print-dependent printer value cannot be flattened: {key}")
                relocated[key] = text
    printers = []
    for model in MODELS:
        variants = []
        for raw in resolved_printers:
            if raw["printer_model"] != model:
                continue
            nozzle = raw["nozzle_diameter"]
            vals = mapped(raw, printer_keys, model)
            vals.update(mapped(relocated, printer_keys, model))
            vals["default_print"] = unquote(raw["default_print_profile"])
            variants.append({"id": stable_id("printer-variant", model + nozzle),
                             "condition": f"tool.nozzle_diameter == {nozzle}", "values": vals})
        printers.append({"kind": "printer", "id": stable_id("printer", model),
                         "name": config[f"printer_model:{model}"]["name"],
                         "condition": f'printer.model == "{model}"', "variants": variants})
    # Alpha12 rejects nonempty ToolPrint overrides on single-tool machines.
    # Put their settings in the matching global Print preset instead.
    tool_print = [{"kind": "tool_print", "id": stable_id("tool_print", "default"),
                   "condition": 'printer.base_model == "KINGROON"',
                   "name": "Kingroon tool settings", "values": {}}]

    prints = []
    for name in public["print"]:
        raw = resolve(config, "print", name)
        nozzle = re.search(r"nozzle_diameter\[0\]==([0-9.]+)", raw["compatible_printers_condition"]).group(1)
        candidates = [mapped(p, tool_keys, name) for p in resolved_printers if p["nozzle_diameter"] == nozzle]
        if not candidates or any(p != candidates[0] for p in candidates):
            raise ValueError(f"Model-specific tool values need conditional branches: {name}")
        vals = candidates[0] | mapped(raw, print_keys, name)
        vals["default_material"] = "Generic PLA @KINGROON"
        vals["default_tool_print"] = "Kingroon tool settings"
        prints.append({"kind": "print", "id": stable_id("print", name), "name": name,
                       "condition": migrate_condition(raw["compatible_printers_condition"]), "values": vals})
    filaments = []
    for name in public["filament"]:
        raw = resolve(config, "filament", name)
        filaments.append({"kind": "filament", "id": stable_id("filament", name), "name": name,
                          "condition": 'printer.base_model == "KINGROON"',
                          "values": mapped(raw, filament_keys, name)})
    report["omitted"] = {k: sorted(v) for k, v in sorted(report["omitted"].items())}
    report["public_presets"] = {kind: len(names) for kind, names in public.items()}
    report["hardware_models"] = len(MODELS)
    report["nozzles"] = list(NOZZLES)
    return {"vendor.yaml": vendor, "printer.yaml": printers, "print.yaml": prints,
            "filament.yaml": filaments, "tool-print.yaml": tool_print}, report


def zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)
    return buf.getvalue()


def build(out, base_url=""):
    config = read_source()
    docs, report = convert(config)
    files = {name: yaml.safe_dump_all(data, sort_keys=False, allow_unicode=False).encode("utf-8")
             for name, data in docs.items()}
    for asset in sorted((ROOT / VENDOR).iterdir()):
        if asset.is_file() and asset.suffix.lower() in (".stl", ".svg", ".png"):
            files[f"assets/{asset.name}"] = asset.read_bytes()
    files["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    files["ATTRIBUTION.md"] = (ROOT / "ATTRIBUTION.md").read_bytes()
    hashes = [{"filename": name, "filehash": hashlib.sha256(data).hexdigest().upper()}
              for name, data in sorted(files.items())]
    files["manifest.json"] = (json.dumps(hashes, indent=2) + "\n").encode()
    index = (f"min_slic3r_version = 3.0.0-alpha12\nmax_slic3r_version = 3.0.0-alpha12\n"
             f"{VERSION} Native Kingroon profiles converted from {report['source_version']}\n").encode()
    base = base_url.rstrip("/") + "/" if base_url else ""
    descriptor = {"id": REPO, "name": "Kingroon FFF", "description": "Kingroon KP3S profiles for PrusaSlicer 3.0 alpha12",
                  "visibility": "", "url": base, "index_url": base + "vendor_indices.zip" if base else ""}
    repository = {f"{VENDOR}/{VERSION}/{name}": data for name, data in files.items()}
    repository["manifest.json"] = (json.dumps(descriptor, indent=2) + "\n").encode()
    repository["vendor_indices.zip"] = zip_bytes({f"{VENDOR}.idx": index})
    repository[f"{VENDOR}/index.idx"] = index
    bundle_zip = zip_bytes({f"{VENDOR}/{VERSION}/{name}": data for name, data in files.items()})
    repository[f"{REPO}-{VENDOR}-{VERSION}.zip"] = bundle_zip
    out.mkdir(parents=True, exist_ok=True)
    archive_path = out / "kingroon-fff.zip"
    archive_path.write_bytes(zip_bytes(repository))
    feed = out / "site"
    feed.mkdir(exist_ok=True)
    for name, data in repository.items():
        target = feed / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    shutil.copyfile(archive_path, feed / archive_path.name)
    (out / "migration-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (feed / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Kingroon profiles</title>'
        '<h1>Kingroon profiles for PrusaSlicer 3.0.0-alpha12</h1>'
        '<p><a href="kingroon-fff.zip">Download the offline repository ZIP</a></p>'
        '<p>Install using Preset sources &amp; updates → Local sources → Add ZIP.</p>'
        '<p>Software validated only. Verify the hardware variant and G-code before printing.</p>'
        '<p><a href="https://github.com/bublinak/KP3S-PrusaSlicer">Source and instructions</a></p>'
        '</html>\n', encoding="utf-8")
    print(f"Built {archive_path} ({archive_path.stat().st_size} bytes)")
    print(json.dumps(report["public_presets"]))
    return archive_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--base-url", default="")
    args = parser.parse_args()
    build(args.output.resolve(), args.base_url)
