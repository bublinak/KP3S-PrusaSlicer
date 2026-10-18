# Kingroon profiles for PrusaSlicer 3

This project builds a native **PrusaSlicer 3.0.0-alpha12** repository for Kingroon KP3S 3.0 and KP3S Pro S1, with separate BLTouch variants. Each model offers 0.2, 0.3, 0.4, 0.5 and 0.6 mm nozzles: 20 configurations, 82 process presets and 42 material presets.

The existing root `Kingroon.ini` and `Kingroon.idx` remain intact as legacy references. The old installation instructions are archived in [docs/LEGACY-PRUSASLICER2.md](docs/LEGACY-PRUSASLICER2.md). The maintained installation uses PrusaSlicer's built-in ZIP importer. The 3.0 conversion uses the newer supplied INI version 1.4.2 in `legacy/1.4.2/`. Generated YAML and ZIPs are build products, not files to edit by hand.

## Download and install

After a successful build and GitHub Pages deployment, the download is available at:

[Kingroon repository ZIP](https://bublinak.github.io/KP3S-PrusaSlicer/kingroon-fff.zip)

Until Pages is deployed, build it locally or download the `kingroon-prusaslicer3` artifact from a successful [Actions run](https://github.com/bublinak/KP3S-PrusaSlicer/actions/workflows/profiles.yml). Extract the Actions artifact wrapper and use the **inner `kingroon-fff.zip`** without unpacking it.

1. Open PrusaSlicer 3.0.0-alpha12.
2. Open **Preset sources & updates**.
3. Under **Local sources**, choose **Add ZIP**, then select `kingroon-fff.zip`.
4. Apply the offered Kingroon installation.
5. Select your exact printer, nozzle and process preset. The associated default tool preset is `Kingroon tool settings`.

The ZIP contains a self-contained repository with an independent `kingroon-fff` ID. No web server or GitHub login is needed to use installed profiles. To update, download and add a newer ZIP. GitHub Pages hosting does **not** register the repository with Prusa's online source service or enable automatic polling in alpha12.

Do not copy the old INI into `resources/profiles` for this version. Alpha12 uses YAML vendor bundles. Do not import GitHub's generic **Download ZIP** source archive as a preset repository.

## GitHub setup

For this fork, enable Actions if GitHub presents the initial fork-workflow confirmation. Under **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**. Pushes to this fork's `main` build, validate and publish the files. A failed validation blocks deployment. No pull request to the original upstream repository is required or planned during testing. Optional pull requests within this fork validate and upload build artifacts but do not deploy Pages.

The generated Pages site also contains versioned profile files, vendor indexes and SHA-256 manifests. These are useful distribution building blocks, but arbitrary remote-source registration remains unsupported by the standard alpha12 UI. A GitLab server can serve the same generated files later.

## Build and verify locally

Use Python 3.12 or newer:

```powershell
python -m pip install -r requirements.txt
python tools/build.py
python tools/validate.py
python tools/validate.py --slicer 'C:\path\to\PrusaSlicer.exe'
```

Output: `dist/kingroon-fff.zip`, `dist/migration-report.json`, and the static download directory `dist/site/`. The native checks use a newly created data directory under `.validation/`, not your installed profile directory. The CLI updater refreshes Prusa's source list during installation; this test may contact Prusa's service, while keeping its repository deselected. Installed profile use and printer discovery do not require that service.

The archive is reproducible for the same source bytes and dependencies. The builder rejects unknown settings, unsupported enum values, missing inheritance and incompatible flattening. The migration report lists omitted metadata and obsolete settings.

## Conversion choices

- Preserve the supplied start/end G-code, relative extrusion (`M83`), Marlin 2 flavor, geometry, nozzle limits, speeds and material settings.
- Preserve the original bed polygon exactly. KP3S is `3x3,181x3,181x181,3x181`, an effective 178 × 178 mm polygon, with a 180 mm height. Pro S1 is a 198 × 198 mm effective polygon with a 200 mm height. These are inherited profile limits, not new measurements.
- Translate nozzle/model compatibility expressions to the new hardware variables.
- Place retraction and other former per-extruder printer settings in native Print settings. Alpha12 rejects nonempty ToolPrint overrides on a single-tool printer; the named tool preset is deliberately empty.
- Move the common source clearance dimensions into Printer settings, where alpha12 defines them.
- Preserve filament-specific retraction overrides, including the supplied Prusament and Alzament TPU additions.
- Repair the pre-existing AmazonBasics TPU reference to a nonexistent `*FLEX*` parent by resolving it to the bundle's existing `*TPU*` base. Both old local copies contain this defect. It is a possible contributor to historical load errors; the old error message was not captured.
- Translate old boolean options that became enums: object labels to OctoPrint labels, enabled vertical shells to `enabled`, disabled supports to `none`.
- Retain bed/thumbnail assets and [upstream attribution](ATTRIBUTION.md). The original CC BY-NC 4.0 terms still apply to the derived profiles and assets.
- Restrict the index to alpha12 until compatibility with later versions is tested. The new bundle version is `3.0.0-alpha1`; this is a profile package version, not a claim that the application is stable.

Old project metadata, preset IDs, extruder colors and wipe-tower placement do not map to native system preset fields. Removed `top_fan_speed = 0`, `infill_only_where_needed = 0` and `clip_multipart_objects = 1` are recorded in the migration report. Other fan settings remain preserved. The source is retained for review.

## Validation and first print

See [VALIDATION.md](VALIDATION.md) for the executed checks and their limits. Software checks do not establish mechanical or thermal suitability. Select BLTouch only if fitted and supported by the machine's firmware. Confirm the actual nozzle, firmware and build limits before running generated G-code on a printer. The inherited 5 mm general retraction and aggressive speed variants remain unchanged; calibrate them on the actual extruder before using them in production.

References: [PrusaSlicer alpha12](https://github.com/prusa3d/PrusaSlicer/releases/tag/version_3.0.0-alpha12), [native updater test guide](https://github.com/prusa3d/PrusaSlicer/blob/version_3.0.0-alpha12/doc/preset-updater-manual-test.md), [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
