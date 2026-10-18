"""Validate the native archive, optionally exercising PrusaSlicer alpha12."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

import yaml

from build import ROOT, REPO, VENDOR, VERSION, MODELS, NOZZLES, convert, read_source


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def check_archive(path):
    with zipfile.ZipFile(path) as archive:
        descriptor = json.loads(archive.read("manifest.json"))
        require(descriptor["id"] == REPO, "Repository ID mismatch")
        with zipfile.ZipFile(io.BytesIO(archive.read("vendor_indices.zip"))) as indexes:
            require(VENDOR + ".idx" in indexes.namelist(), "Missing vendor index")
            require(VERSION in indexes.read(VENDOR + ".idx").decode(), "Version missing from index")
        prefix = f"{VENDOR}/{VERSION}/"
        manifest = json.loads(archive.read(prefix + "manifest.json"))
        for entry in manifest:
            content = archive.read(prefix + entry["filename"])
            require(hashlib.sha256(content).hexdigest().upper() == entry["filehash"],
                    f"Checksum mismatch: {entry['filename']}")
        hardware = list(yaml.safe_load_all(archive.read(prefix + "vendor.yaml")))
        require(sum(x["kind"] == "printer_config" for x in hardware) == 20, "Expected 20 hardware configurations")
        require(sum(x["kind"] == "tool" for x in hardware) == 5, "Expected five nozzles")
        docs, report = convert(read_source())
        require(report["public_presets"] == {"printer": 20, "print": 82, "filament": 42}, "Source preset count changed")
        for name, expected in docs.items():
            require(list(yaml.safe_load_all(archive.read(prefix + name))) == expected, f"Generated YAML mismatch: {name}")
        # Single-tool printers must have no ToolPrint overrides in alpha12.
        require(docs["tool-print.yaml"][0]["values"] == {}, "Single-tool overrides would prevent slicing")
        for printer in docs["printer.yaml"]:
            for variant in printer["variants"]:
                require(variant["values"]["gcode_flavor"] == "marlin2", "Firmware changed")
                require(variant["values"]["use_relative_e_distances"], "Extrusion mode changed")
                require("G29" in variant["values"]["start_gcode"] if "BLTOUCH" in printer["condition"]
                        else "G29" not in variant["values"]["start_gcode"], "BLTouch homing mismatch")
        require(all(p["values"]["retract_length"] == 5 for p in docs["print.yaml"]), "Source retraction changed")
    print("Archive, hashes, source preset counts and machine invariants verified.", flush=True)


def cube(path):
    vertices = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
                (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    path.write_text("solid cube\n" + "".join(
        "facet normal 0 0 0\nouter loop\n" + "".join("vertex %s %s %s\n" % vertices[i] for i in face)
        + "endloop\nendfacet\n" for face in faces) + "endsolid cube\n", encoding="ascii")


def native_checks(slicer, archive, work):
    work.mkdir(parents=True, exist_ok=True)
    test = Path(tempfile.mkdtemp(prefix="alpha12-", dir=work))
    data = test / "data"
    shared = data / "shared_runtime"
    shared.mkdir(parents=True)
    # Keep the public Prusa source deselected if the CLI refreshes its source list.
    (shared / "RepositoryManifest.json").write_text(json.dumps([{
        "id": "prusa-research-fff", "name": "Prusa FFF", "description": "Prusa FFF",
        "visibility": "", "selected": False, "uuid": "62c77283-55b8-42e7-8dea-f08e2ba1250f",
        "url": "https://preset-repo-api.prusa3d.com/v2/repos/prusa-research-fff/",
        "index_url": "https://preset-repo-api.prusa3d.com/v2/repos/prusa-research-fff/vendor_indices.zip"
    }]), encoding="utf-8")

    def run(label, *args, timeout=120):
        command = [str(slicer), "--datadir", str(data), *map(str, args)]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        (test / (label + ".log")).write_text(result.stdout, encoding="utf-8")
        require(result.returncode == 0, f"{label} failed; see {test}")
        require('"error":' not in result.stdout, f"{label} returned an updater error; see {test}")
        require("Loading bundle" not in result.stdout or "failed with error" not in result.stdout,
                f"{label}: bundle parsing failed; see {test}")
        return result.stdout

    run("add-zip", "--preset-update-add-local", archive)
    run("install-zip", "--preset-update")
    installed = data / "presets/local" / REPO / VENDOR
    require((installed / "vendor.yaml").exists(), f"ZIP did not install; see {test}")
    # Confirm the updater installed exactly the current archive's profile bytes.
    with zipfile.ZipFile(archive) as package:
        for name in ("vendor.yaml", "printer.yaml", "print.yaml", "filament.yaml", "tool-print.yaml"):
            require((installed / name).read_bytes() == package.read(f"{VENDOR}/{VERSION}/{name}"),
                    f"Installed file differs: {name}")
    run("models", "--query-printer-models", "--output", test / "models.json")
    models = [m for m in json.loads((test / "models.json").read_text())["printer_models"]
              if m.get("vendor_id") == VENDOR]
    require(len({m["name"] for m in models}) == 4, "Expected four Kingroon model names")
    require(sum(len(m["variants"]) for m in models) == 20, "Expected 20 Kingroon variants")
    source = read_source()
    stl = test / "cube.stl"
    cube(stl)
    total_slices = 0
    # Validate nozzle filtering for all models/nozzles and slice each hardware variant.
    for model in MODELS:
        model_name = source[f"printer_model:{model}"]["name"]
        for nozzle in NOZZLES:
            label = model + "-" + nozzle
            printer = model_name + " " + nozzle + " mm"
            output = test / (label + ".json")
            run(label + "-profiles", "--printer-profile", printer,
                "--query-print-tool-filament-profiles", "--output", output)
            profiles = json.loads(output.read_text())["print_profiles"]
            require(profiles and all(f"({nozzle} mm nozzle)" in p["name"] for p in profiles),
                    f"Nozzle compatibility filter failed: {printer}")
            print_name = next(p["name"] for p in profiles if "0.16 mm OPTIMAL (" in p["name"])
            args = ["--printer-profile", printer, "--print-profile", print_name,
                    "--tool-print-profile", "Kingroon tool settings", "--material-profile", "Generic PLA @KINGROON"]
            gcode = test / (label + ".gcode")
            run(label + "-slice", *args, "--export-gcode", "--output", gcode, stl)
            require(gcode.exists() and gcode.stat().st_size > 1000,
                    f"CLI returned success without G-code: {printer}; see {test}")
            commands = [line.split(";", 1)[0].strip() for line in gcode.read_text().splitlines()]
            require("G28" in commands and "M83" in commands, f"Homing/extrusion missing: {printer}")
            require(("G29" in commands) == ("BLTOUCH" in model), f"BLTouch mismatch: {printer}")
            require("M190 S60" in commands and "M109 S200" in commands, f"PLA temperature mismatch: {printer}")
            total_slices += 1
            print(f"Validated {printer}", flush=True)
    # Inspect resolved overrides for the inherited TPU defect and added local materials.
    for material, expected in (("AmazonBasics TPU @KINGROON", 2.5),
                               ("Prusament TPU 95A @KINGROON", 1.2),
                               ("Alzament TPU 95A @KINGROON", 1.2)):
        output = test / (material.split(" @")[0].replace(" ", "-") + ".json")
        run(output.stem, "--printer-profile", "Kingroon KP3S 3.0 0.4 mm",
            "--print-profile", "0.16 mm OPTIMAL (0.4 mm nozzle) @KINGROON",
            "--tool-print-profile", "Kingroon tool settings", "--material-profile", material, "--save", output)
        config = json.loads(output.read_text())["configuration"]
        require(expected in config["filament_settings"]["retract_length"], f"Material retraction lost: {material}")
    summary = {"slicer": "3.0.0-alpha12", "installed_via_zip": True, "models": 4,
               "variants": 20, "sliced_variants": total_slices,
               "material_override_checks": 3, "physical_validation": False}
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)
    print(f"Logs and test output: {test}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "dist/kingroon-fff.zip")
    parser.add_argument("--slicer", type=Path)
    parser.add_argument("--work", type=Path, default=ROOT / ".validation")
    args = parser.parse_args()
    check_archive(args.archive.resolve())
    if args.slicer:
        native_checks(args.slicer.resolve(), args.archive.resolve(), args.work.resolve())
