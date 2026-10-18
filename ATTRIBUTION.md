# Attribution

The Kingroon profiles and bed/thumbnail assets originate from [RyanT95/KP3S-Prusa](https://github.com/RyanT95/KP3S-Prusa), licensed under Creative Commons Attribution-NonCommercial 4.0 International. The full license is retained in `LICENSE`.

The existing repository root preserves version 1.4.0. The native PrusaSlicer 3 conversion uses the user-supplied version 1.4.2, preserved in `legacy/1.4.2/Kingroon.ini`. Its index records added Prusament and Alzament TPU support and the Alzament TPU volumetric-speed adjustment. Those later changes are preserved as supplied; their authorship was not independently established.

The conversion and packaging scripts resolve the original inheritance, map settings to the alpha12 configuration schema, and generate native YAML and SHA-256 manifests. This is a format conversion, not manufacturer certification or evidence of physical printer testing.

The configuration schema in `schema/3.0.0-alpha12.json` was exported by PrusaSlicer 3.0.0-alpha12 using `--export-config-schema`. PrusaSlicer is developed by Prusa Research and contributors under AGPL-3.0. See [PrusaSlicer](https://github.com/prusa3d/PrusaSlicer/tree/version_3.0.0-alpha12).
