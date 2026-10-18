# Kingroon profiles for PrusaSlicer 3

Native profile repository for **PrusaSlicer 3.0.0-alpha12**, maintained in [bublinak/KP3S-PrusaSlicer](https://github.com/bublinak/KP3S-PrusaSlicer). Changes remain in this fork while they are being tested; no upstream pull request is part of this workflow.

Supports Kingroon KP3S 3.0 and KP3S Pro S1, each with standard and BLTouch configurations. There are **four printer entries**, each with selectable **0.2, 0.3, 0.4, 0.5 and 0.6 mm nozzles**. The default is 0.4 mm. The package also contains 82 process presets and 42 material presets.

## Install through PrusaSlicer

1. Download **[kingroon-fff.zip](https://bublinak.github.io/KP3S-PrusaSlicer/kingroon-fff.zip)** after the Pages deployment has completed. If Pages is not available, use the tested local build or the `kingroon-prusaslicer3` artifact from a successful [GitHub Actions run](https://github.com/bublinak/KP3S-PrusaSlicer/actions/workflows/profiles.yml).
2. In PrusaSlicer, open **Preset sources & updates**.
3. Under **Local sources**, click **Add ZIP** and select `kingroon-fff.zip`.
4. Apply the Kingroon installation offered by PrusaSlicer.
5. Select your hardware model once, then choose the installed nozzle in its printer configuration selector. Compatible process presets and the default process follow the selected diameter.

Keep `kingroon-fff.zip` intact. If downloading an Actions artifact, extract the outer artifact ZIP first, then select the inner `kingroon-fff.zip`. GitHub's **Code → Download ZIP** is the source repository, not an importable profile package.

Updates use the same built-in ZIP importer with a newer package. Version `3.0.0-alpha2` consolidates the old per-nozzle printer entries into one entry per hardware model. Installed profiles work locally; automatic online update registration with Prusa is not configured.

## Testing and maintenance

The package is checked for four printer entries and five nozzle choices. Software validation covers all 20 model/nozzle combinations, including nozzle-dependent presets and three TPU retraction checks. Physical printer testing is still pending. Select the BLTouch variant only for a machine equipped and configured for it.

- [Build, install and GitHub Pages details](PRUSASLICER3.md)
- [Executed checks and limitations](VALIDATION.md)
- [Attribution and licensing](ATTRIBUTION.md)
- [Historical PrusaSlicer 2.x documentation](docs/LEGACY-PRUSASLICER2.md)

The 2.x INI files are retained as source/reference material. The current PrusaSlicer 3 installation uses the native ZIP importer described above.
