# Traeger HASS component

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

_Component to integrate with [Traeger WiFire Grills][traeger]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Shows various temperature readings from the grill or accessories
`water_heater` | Allows temperature control of the grill

![device][deviceimg]
![grill][grillimg]
![probe][probeimg]

## Installation (Manual)

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `traeger`.
4. Download _all_ the files from the `custom_components/traeger/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Traeger"


## Installation (HACS)

1. Add this repository to HACS
2. Search for Traeger in HACS

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[traeger]: https://www.traegergrills.com/
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[deviceimg]: device.png
[probeimg]: probe.png
[grillimg]: grill.png
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/custom-components/blueprint.svg?style=for-the-badge
[releases]: https://github.com/sebirdman/hass_traeger/releases
