# Validation record

Date: 2026-10-18. Reference application: the user's installed Windows PrusaSlicer 3.0.0-alpha12. Source repository baseline: `2b5f86f` (`main`). Native profile source: preserved local INI version 1.4.2.

## Repeatable checks

`tools/validate.py` checks the ZIP structure, every version-manifest SHA-256, exact generated YAML, public preset counts, firmware flavor, extrusion mode, BLTouch homing and source retraction. Rebuilding from the same input bytes produces the same archive.

With `--slicer`, it creates a fresh test data directory and:

1. Adds `kingroon-fff.zip` using `--preset-update-add-local` and installs it using `--preset-update`.
2. Compares the installed YAML bytes with the generated archive.
3. Queries printer discovery: four model names and 20 model/nozzle configurations.
4. Queries compatible process, tool and material profiles for each configuration, checking nozzle filters.
5. Slices a 10 mm cube for every configuration and requires an actual nonempty G-code file. Checks `G28`, `M83`, PLA heating commands, and `G29` only for BLTouch configurations.
6. Exports resolved configurations for AmazonBasics TPU, Prusament TPU 95A and Alzament TPU 95A, checking filament retraction overrides.

Logs and generated G-code stay under `.validation/`. A completed run writes `.validation/summary.json`. CI publishes this summary with the installable ZIP and migration report.

The software checks passed locally for all 20 model/nozzle configurations and all three TPU override checks. They cover one representative process/material slice per hardware configuration, not every process/material combination.

## Findings incorporated into the conversion

- The supplied AmazonBasics TPU preset inherits from missing `*FLEX*`; use the existing `*TPU*` base during conversion and retain the input file unchanged.
- Alpha12 rejects nonempty ToolPrint overrides on a single-tool machine. Put inherited retraction and nozzle-layer limits in the Print profile instead.
- Alpha12's CLI can return exit status 0 after a slicing validation error without producing G-code. The checks require the output file and its expected commands, not just the return code.
- Common source clearance dimensions now belong to the Printer category; the converter moves them only after checking every process agrees.
- The CLI prints missing physical-printer-storage messages in a new test directory and virtual bed-model path errors for both the shipped Prusa bundle and custom bundle. These do not prevent the tested CLI slices. Visual bed rendering in the GUI has not been verified.

## Limits

No physical printer was connected, moved or heated. Firmware suitability, BLTouch wiring and behavior, nozzle size, bed limits, retraction and volumetric limits still need verification on the actual printer. No claim of manufacturer approval or physical calibration is made.

GitHub Actions and Pages require a run in the target repository after the branch is pushed. Until that succeeds and Pages is enabled, the Pages download link is prospective; the locally built ZIP is available for testing. Automatic remote-source registration/polling from GitHub was not established.
