# BL4 Loot Filter

A Borderlands 4 SDK mod that allows you to filter and teleport ground loot based on your preferences.

## Features

- **Teleport Loot**: Teleport loot you want right in front of you to pick up
- **Delete Loot**: Get loot you don't want off of your screen
- **Teleport Unrecognized Loot**: Teleport any loot not understood by the mod right behind you. If you do encounter unrecognized loot, please report it.
- **Configurable Filtering**: Enable/disable specific item types, rarities, and manufacturers

## Installation

1. Install the BL4 SDK following the instructions at https://bl-sdk.github.io/oak2-mod-db/
2. Download the zip folder on the releases page and unzip it into your sdk_mods folder

## Configuration

Edit `config.json` to customize which loot types you want to see along the following axes:

- Rarity
- Item type
- Weapon type
- Manufacturer
- Presence of firmware

Set values to `true` to teleport them or `false` to delete them.

You will also need to configure your hotkeys in game in the modding SDK console.
If desired, you can bind all functions to the same hotkey so one press will teleport loot you want,
delete loot you don't want, and bring any unrecognized loot behind you for manual inspection.

## Future Goals

The `legendaries.json` file contains an incomplete database of legendary gear.
Once that is comprehensive I'd like to update the config and filtering logic 
to go by specific legendary rather than just type and manufacturer.
Users of this mod can help with this - when you teleport a legendary drop
you can open up the modding console which may display a message about an unknown legendary identifier.
If it does, please reach out and let me know the identifier displayed as well as which legendary you teleported.

I'd also love to have more granular filtering based on item parts, but I'm not sure where to get that information right now.
If you have ideas, please contact me.

## License

GPL-3.0 - See LICENSE file for details

## Author

Lango

## Feedback & Issues

Please report any issues, unrecognized items, or missing legendary information at https://github.com/jlangowells/bl4_loot_filter/issues.
You can also reach me on the [Borderlands Modding Discord](https://discord.com/invite/bXeqV8Ef9R) as @Lango.

## Acknowledgements

This mod is inspired by RedxYeti's [GroundLootFilters](https://github.com/RedxYeti/yeti-bl4-sdk/tree/main/GroundLootHelpers) and I've adapted significant portions of that implementation.

Credits also go to @SlippyCheeze on the [Borderlands Modding Discord](https://discord.com/invite/bXeqV8Ef9R) for the logic to parse rarity information from loot beams.
