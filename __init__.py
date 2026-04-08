from __future__ import annotations

import enum
import json
import math
import importlib.resources

from dataclasses import dataclass
from mods_base import build_mod, get_pc, keybind, NestedOption, BoolOption, GroupedOption
from unrealsdk import make_struct, find_all
from unrealsdk.unreal import UObject, IGNORE_STRUCT
from unrealsdk.logging import info, warning

TELEPORT_DISTANCE = 200.0

# Load loot filter config
CONFIG: dict = {}
try:
    config_text = importlib.resources.read_text(__package__ or ".", "config.json")
    CONFIG = json.loads(config_text)
except (FileNotFoundError, json.JSONDecodeError) as e:
    warning(f"Failed to load config.json: {e}")

# Load legendary data
LEGENDARY_MAP: dict = {}
try:
    legendary_text = importlib.resources.read_text(__package__ or ".", "legendaries.json")
    LEGENDARY_MAP = json.loads(legendary_text)
except (FileNotFoundError, json.JSONDecodeError) as e:
    warning(f"Failed to load legendaries.json: {e}")

@enum.verify(enum.UNIQUE)
class LootType(enum.StrEnum):
    """Categories of loot items (consumables vs gear)."""
    UNKNOWN   = enum.auto()
    PICKUPS   = enum.auto()
    GEAR      = enum.auto()

@enum.verify(enum.UNIQUE)
class PickupType(enum.StrEnum):
    """Categories of pickup items."""
    UNKNOWN        = enum.auto()
    ERIDIUM        = enum.auto()
    MONEY          = enum.auto()
    AMMO           = enum.auto()
    HEALTH         = enum.auto()
    SHIELDBOOSTER  = enum.auto()
    MISSION        = enum.auto()

@enum.verify(enum.UNIQUE)
class Rarity(enum.StrEnum):
    """Rarity levels for gear items."""
    UNKNOWN        = enum.auto()
    COMMON         = enum.auto()
    UNCOMMON       = enum.auto()
    RARE           = enum.auto()
    EPIC           = enum.auto()
    LEGENDARY      = enum.auto()
    PEARLESCENT    = enum.auto()

@enum.verify(enum.UNIQUE)
class ItemType(enum.StrEnum):
    """Types of gear items."""
    UNKNOWN         = enum.auto()
    WEAPON          = enum.auto()
    REPKIT          = enum.auto()
    HEAVY_ORDNANCE  = enum.auto()
    GRENADE         = enum.auto()
    CLASS_MOD       = enum.auto()
    SHIELD          = enum.auto()
    ENHANCEMENT     = enum.auto()

@enum.verify(enum.UNIQUE)
class WeaponType(enum.StrEnum):
    """Types of weapons."""
    UNKNOWN         = enum.auto()
    SNIPER          = enum.auto()
    SHOTGUN         = enum.auto()
    ASSAULT_RIFLE   = enum.auto()
    SMG             = enum.auto()
    PISTOL          = enum.auto()

@enum.verify(enum.UNIQUE)
class Manufacturer(enum.StrEnum):
    """Gear manufacturers."""
    UNKNOWN         = enum.auto()
    ORDER           = enum.auto()
    RIPPER          = enum.auto()
    JAKOBS          = enum.auto()
    MALIWAN         = enum.auto()
    DAEDALUS        = enum.auto()
    TORGUE          = enum.auto()
    VLADOF          = enum.auto()
    TEDIORE         = enum.auto()
    ATLAS           = enum.auto()
    COV             = enum.auto()
    HYPERION        = enum.auto()

@enum.verify(enum.UNIQUE)
class VaultHunter(enum.StrEnum):
    """Vault Hunter classes for class mods."""
    UNKNOWN         = enum.auto()
    RAFA            = enum.auto()
    VEX             = enum.auto()
    AMON            = enum.auto()
    HARLOWE         = enum.auto()
    CASH            = enum.auto()

MANUFACTURER_MAP = {
    'JAK': Manufacturer.JAKOBS,
    'MAL': Manufacturer.MALIWAN,
    'TOR': Manufacturer.TORGUE,
    'VLA': Manufacturer.VLADOF,
    'TED': Manufacturer.TEDIORE,
    'BOR': Manufacturer.RIPPER,
    'ORD': Manufacturer.ORDER,
    'DAD': Manufacturer.DAEDALUS,
    'ATLAS': Manufacturer.ATLAS,
    'COV': Manufacturer.COV,
    'HYP': Manufacturer.HYPERION,
}

WEAPON_TYPE_MAP = {
    'Sniper': WeaponType.SNIPER,
    'Shotguns': WeaponType.SHOTGUN,
    'shotgun': WeaponType.SHOTGUN,
    'AssaultRifles': WeaponType.ASSAULT_RIFLE,
    'Assault': WeaponType.ASSAULT_RIFLE,
    'SMG': WeaponType.SMG,
    'Pistols': WeaponType.PISTOL,
    'Pistol': WeaponType.PISTOL,
}

VAULT_HUNTER_MAP = {
    'Gravitar': VaultHunter.HARLOWE,
    'ExoSoldier': VaultHunter.RAFA,
    'Paladin': VaultHunter.AMON,
    'DarkSiren': VaultHunter.VEX,
    'RoboDealer': VaultHunter.CASH,
}

LOOT_TYPE_MAP = {
    'Pickups': LootType.PICKUPS,
    'Gear': LootType.GEAR,
}

PICKUP_TYPE_MAP = {
    'Ammo': PickupType.AMMO,
    'ammo': PickupType.AMMO, # Some pickups have only lowercase ammo
    'Money': PickupType.MONEY,
    'Eridium': PickupType.ERIDIUM,
    'Health': PickupType.HEALTH,
    'Mission': PickupType.MISSION,
    'ShieldBooster': PickupType.SHIELDBOOSTER,
    'ShieldBoosters': PickupType.SHIELDBOOSTER,
}

FIRMWARE_MAP = {
    ItemType.SHIELD: 'SHIELD',
    ItemType.CLASS_MOD: 'CLASS_MOD',
    ItemType.REPKIT: 'REPKIT',
    ItemType.ENHANCEMENT: 'ENHANCEMENT',
    ItemType.HEAVY_ORDNANCE: 'ORDNANCE',
    ItemType.GRENADE: 'ORDNANCE',
}

COLOR_RARITY_MAP = {
    bytes((0xAB, 0xD1, 0x03, 0x3F, 0x1B, 0x67, 0xFB, 0x3E,
           0xE8, 0xBB, 0x1F, 0x3F, 0x00, 0x00, 0x80, 0x3F)): Rarity.COMMON,
    bytes((0x51, 0x30, 0xC3, 0x3D, 0x70, 0xEF, 0x0E, 0x3F,
           0x9B, 0x3C, 0xE5, 0x3D, 0x00, 0x00, 0x80, 0x3F)): Rarity.UNCOMMON,
    bytes((0x50, 0x8D, 0x97, 0x3C, 0xC3, 0xA0, 0xAC, 0x3E,
           0xCF, 0x32, 0x17, 0x3F, 0x00, 0x00, 0x80, 0x3F)): Rarity.RARE,
    bytes((0x6E, 0x69, 0xF5, 0x3E, 0x79, 0xE6, 0x65, 0x3D,
           0x44, 0x8B, 0x28, 0x3F, 0x00, 0x00, 0x80, 0x3F)): Rarity.EPIC,
    bytes((0x00, 0x00, 0x80, 0x3F, 0x8F, 0xA6, 0x6A, 0x3E,
           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x3F)): Rarity.LEGENDARY,
    bytes((0xB9, 0x72, 0x9E, 0x3E, 0x00, 0x00, 0x80, 0x3F,
           0xA4, 0xFC, 0x24, 0x3F, 0x00, 0x00, 0x80, 0x3F)): Rarity.PEARLESCENT,
}

NIAGARA_TRUE  = bytes((0xFF, 0xFF, 0xFF, 0xFF))
NIAGARA_FALSE = bytes((0x00, 0x00, 0x00, 0x00))

FilterConfig = {}

def _populate_filter_config_and_build_options():
    options = []

    # Set up firmware filters
    FilterConfig["FIRMWARE"] = {}
    for item_type in set(FIRMWARE_MAP.values()):
        FilterConfig["FIRMWARE"][item_type] = BoolOption(
            value=True,
            identifier=item_type,
            description=f"{item_type} items with firmware",
        )
    options.append(GroupedOption(
        identifier="Firmware",
        description="Firmware Filters",
        children=list(FilterConfig["FIRMWARE"].values())
    ))

    # Set up pickup filters
    FilterConfig["PICKUPS"] = {}
    pickup_options = []
    for pickup_type in set(PICKUP_TYPE_MAP.values()):
        # Allow gun type ammo filtering
        if pickup_type == PickupType.AMMO:
            FilterConfig["PICKUPS"]["AMMO"] = {}
            for weapon_type in set(WEAPON_TYPE_MAP.values()):
                FilterConfig["PICKUPS"]["AMMO"][weapon_type] = BoolOption(
                    value=True,
                    identifier=weapon_type,
                    description=f"{weapon_type} ammo",
                )
            pickup_options.append(NestedOption(
                identifier="Ammo",
                description="Ammo filters by weapon type",
                children=list(FilterConfig["PICKUPS"]["AMMO"].values())
            ))
        else:
            FilterConfig["PICKUPS"][pickup_type] = BoolOption(
                value=True,
                identifier=pickup_type,
                description=f"{pickup_type} pickups",
            )
            pickup_options.append(FilterConfig["PICKUPS"][pickup_type])
    options.append(GroupedOption(
        identifier="Pickups",
        description="Pickup Filters",
        children=pickup_options
    ))

    return options

@dataclass(slots=True)
class LootInfo:
    """Represents a loot item with all its parsed attributes."""
    loot_type:    LootType     = LootType.UNKNOWN
    pickup_type:  PickupType   = PickupType.UNKNOWN
    rarity:       Rarity       = Rarity.UNKNOWN
    item_type:    ItemType     = ItemType.UNKNOWN
    weapon_type:  WeaponType   = WeaponType.UNKNOWN
    manufacturer: Manufacturer = Manufacturer.UNKNOWN
    vault_hunter: VaultHunter  = VaultHunter.UNKNOWN
    legendary_name: str        = ''
    anointment:   bool         = False
    firmware:     bool         = False
    shiny:        bool         = False
    legendary:    bool         = False

    # Debugging related info
    raw_body_data: str = ''
    raw_material_data: str = ''

    def __str__(self):
        """Return a string representation of the loot item."""
        lines = []
        if self.pickup_type != PickupType.UNKNOWN:
            lines.append(f"Pickup Type: {self.pickup_type}")
        if self.item_type != ItemType.UNKNOWN:
            lines.append(f"Item Type: {self.item_type}")
        if self.rarity != Rarity.UNKNOWN:
            lines.append(f"Rarity: {self.rarity}")
        if self.legendary_name:
            lines.append(f"Legendary: {self.legendary_name}")
        if self.weapon_type != WeaponType.UNKNOWN:
            lines.append(f"Weapon: {self.weapon_type}")
        if self.manufacturer != Manufacturer.UNKNOWN:
            lines.append(f"Manufacturer: {self.manufacturer}")
        if self.vault_hunter != VaultHunter.UNKNOWN:
            lines.append(f"Class: {self.vault_hunter}")
        if self.raw_body_data:
            lines.append(f"Raw Body Data: {self.raw_body_data}")
        if self.raw_material_data:
            lines.append(f"Raw Material Data: {self.raw_material_data}")
        return "\n".join(lines) if lines else "Unknown Loot"

    @classmethod
    def from_inventory_pickup(cls, item: UObject) -> LootInfo:
        """Create a LootInfo instance by parsing an InventoryPickup UObject."""
        loot = cls()

        # Get data from the BodyData, which contains info about item type and manufacturer.
        if item.BodyData:
            if item.BodyData.Outer:
                loot.raw_body_data = item.BodyData.Outer.Name
                # Contains a leading '/' so we strip the 0th element.
                body_data = loot.raw_body_data.split('/')[1:]
                if body_data[0] != 'Game':
                    warning(f'Expected Game in Body Data but got {body_data}')
                # Some DLC items, e.g. C4SH class mods, have an extra /DLC/<DLC_NAME> layer
                # in the BodyData, so we need to check for that and adjust accordingly.
                if body_data[1] == 'DLC':
                    body_data = body_data[2:]

                match body_data[1]:
                    case 'Gear':
                        loot.loot_type = LootType.GEAR
                        loot._process_gear_data(body_data[2:])
                        if (beam := item.AttractEffectComponent):
                            loot._process_loot_beam(beam)
                        else:
                            warning(f'No Loot Beam found for gear item {loot}')
                    case 'Pickups':
                        loot.loot_type = LootType.PICKUPS
                        loot._process_pickup_data(body_data[2:])
                    case 'Missions':
                        loot.loot_type = LootType.PICKUPS
                        loot.pickup_type = PickupType.MISSION
                    case _:
                        warning(f'Unknown loot type {body_data[1]} in Body Data {body_data}')
            else:
                warning(f'No Outer found for Body Data in item {item.BodyData}')

        if item.RootPrimitiveComponent.GetNumMaterials() > 0:
            # There's a lot of info in the 0th material for both gear and pickups.
            loot.raw_material_data = item.RootPrimitiveComponent.GetMaterial(0).Name
            loot._process_material_data()

        return loot

    def _process_gear_data(self, data: list[str]):
        manufacturer = ''
        item_type = data[0]
        match item_type:
            case 'Weapons':
                self.item_type = ItemType.WEAPON
                weapon_type = data[1]
                self.weapon_type = WEAPON_TYPE_MAP.get(weapon_type, WeaponType.UNKNOWN)
                if self.weapon_type == WeaponType.UNKNOWN:
                    warning(f'Unexpected Weapon Type: {weapon_type} in {data}')
                manufacturer = data[2]
            case 'GrenadeGadgets':
                self.item_type = ItemType.GRENADE
                # Grenade format is Body_<MANUFACTURER>_GRN_Inv
                # so we want the 1th element split on underscore
                manufacturer = data[3].split('_')[1]
            case 'Gadgets':
                gadget_type = data[1]
                manufacturer = data[2]
                if gadget_type == 'HeavyWeapons':
                    self.item_type = ItemType.HEAVY_ORDNANCE
                else:
                    warning(f'Unexpected Gadgets Type: {gadget_type} in {data}')
            case 'RepairKits':
                self.item_type = ItemType.REPKIT
            case 'Enhancements':
                self.item_type = ItemType.ENHANCEMENT
            case 'Shields':
                self.item_type = ItemType.SHIELD
                manufacturer = data[2]
            case 'ClassMods':
                self.item_type = ItemType.CLASS_MOD
                # Class mod format is Body_<VaultHunter>_ClassMod
                # so we want the 1th element split on underscore
                vh = data[2].split('_')[1]
                self.vault_hunter = VAULT_HUNTER_MAP.get(vh, VaultHunter.UNKNOWN)
                if self.vault_hunter == VaultHunter.UNKNOWN:
                    warning(f'Unexpected Vault Hunter: {vh} in {data}')
            case _:
                warning(f'Unexpected Item Type: {item_type} in {data}')
        self.manufacturer = MANUFACTURER_MAP.get(manufacturer, Manufacturer.UNKNOWN)
        if manufacturer != '' and self.manufacturer == Manufacturer.UNKNOWN:
            warning(f'Unexpected Manufacturer: {manufacturer} in {data}')

    def _process_pickup_data(self, data: list[str]):
        self.pickup_type = PICKUP_TYPE_MAP.get(data[0], PickupType.UNKNOWN)
        if self.pickup_type == PickupType.UNKNOWN:
            warning(f'Unexpected Pickup Type: {data[0]} in {data}')

    def _process_loot_beam(self, beam):
        # Get data from the Loot Beam Niagara component parameters, which contain rarity and more.
        parameter_data = bytes(beam.OverrideParameters.ParameterData)
        for var in beam.OverrideParameters.SortedParameterOffsets:
            match str(var.Name):
                case str('User.HasFirmware'):
                    raw = parameter_data[var.Offset:var.Offset+4]
                    value = raw != NIAGARA_FALSE
                    self.firmware = value

                case 'User.IsLegendary':
                    raw = parameter_data[var.Offset:var.Offset+4]
                    value = raw != NIAGARA_FALSE
                    self.legendary = value

                case str('User.HasAnointment'):
                    raw = parameter_data[var.Offset:var.Offset+4]
                    value = raw != NIAGARA_FALSE
                    self.anointment = value

                case str('User.IsShiny'):
                    raw = parameter_data[var.Offset:var.Offset+4]
                    value = raw != NIAGARA_FALSE
                    self.shiny = value

                case str('User.Color'):
                    raw = parameter_data[var.Offset:var.Offset+16]
                    value = COLOR_RARITY_MAP.get(raw)
                    if isinstance(value, Rarity):
                        self.rarity = value
                    else:
                        warning(f'Unknown Niagara color: {raw.hex()} in item {self}')

    def _process_material_data(self):
        material_data = self.raw_material_data.split('_')
        match material_data[0]:
            # MI has most pickups, M is used for other pickups like shield boosters.
            case 'MI' | 'M':
                pickup = material_data[1]
                if pickup in PICKUP_TYPE_MAP:
                    self.loot_type = LootType.PICKUPS
                    self.pickup_type = PICKUP_TYPE_MAP.get(pickup, PickupType.UNKNOWN)
                else:
                    warning(f'Unknown pickup type {pickup} in {material_data}')
                if self.pickup_type == PickupType.AMMO:
                    # Ammo has the weapon type in element 2, e.g. MI_AMMO_SMG
                    weapon = material_data[2]
                    self.weapon_type = WEAPON_TYPE_MAP.get(weapon, WeaponType.UNKNOWN)
                    if self.weapon_type == WeaponType.UNKNOWN:
                        warning(f'Unknown weapon type {weapon} for ammo in {material_data}')
            # MID is gear and may contain information we don't already have from BodyData,
            # like repkit/enhancement manufacturer.
            # Class mods also apparently have a manufacturer although it's not clear why.
            case 'MID':
                if material_data[1] != 'M':
                    warning(f'Unexpected MID material format: {material_data}')
                manufacturer = material_data[2]
                # Legendary items have a different material format and don't include manufacturer.
                # However, each legendary has a unique identifier in element 4, which
                # we can use to determine not only the manufacturer but the specific legendary.
                if manufacturer == 'LEG':
                    self.rarity = Rarity.LEGENDARY
                    legendary = material_data[4]
                    if legendary in LEGENDARY_MAP:
                        manufacturer = LEGENDARY_MAP[legendary].get('manufacturer', '')
                        self.legendary_name = LEGENDARY_MAP[legendary].get('name', '')
                    else:
                        warning(f'Unknown legendary identifier {legendary} in {material_data}')
                elif manufacturer in MANUFACTURER_MAP:
                    self.manufacturer = MANUFACTURER_MAP.get(manufacturer, Manufacturer.UNKNOWN)
                else:
                    warning(f'Unknown manufacturer {manufacturer} in {material_data}')       
            case _:
                warning(f'Unknown material prefix {material_data[0]} in {material_data}')



# Items of the day are technically pickups but they aren't loot on the ground,
# so we need to filter them out.
def get_items_of_the_day() -> list:
    """Return a list of current IotD pickups available from vending machines."""
    iotds = []
    pc = get_pc()
    for machine in find_all("OakVendingMachine", False):
        if not machine or machine == machine.Class.ClassDefaultObject:
            continue
        current_iotd = machine.GetIOTDForPlayer(pc)
        if current_iotd:
            iotds.append(current_iotd)
    return iotds

def get_loot() -> list:
    """Gather and return all ground loot pickup objects in the world."""
    loot = []
    iotd_pickups = get_items_of_the_day()
    for drop in find_all("InventoryPickup", False):
        # Filter out invalid drops or items of the day as they aren't actually ground loot.
        if (
            not drop or drop == drop.Class.ClassDefaultObject or
            drop in iotd_pickups or not drop.RootPrimitiveComponent
            or drop.RootPrimitiveComponent.GetNumMaterials() == 0
        ):
            continue
        loot.append(drop)
    return loot

def filter_loot(item: LootInfo, unwanted: bool = False, unknown: bool = False) -> bool:
    """
    Filter an item based on loot filter configuration.

    Pass unwanted to get items that should be delteted instead of teleported,
    and unknown to get items that don't fit any known category for debugging purposes.
    
    Config structure:
    - LootType (top): GEAR, AMMO, MONEY, ERIDIUM, HEALTH, MISSION, etc.
    - For GEAR: { Rarity { ItemType { details } } }
    - For consumables: boolean value
    """
    loot_type = item.loot_type
    passes_filter = False

    if loot_type == LootType.UNKNOWN:
        warning(f"Unknown loot type for item: {item}")
        return unknown

    # Always take shinies. I don't see a reason to make this configurable.
    if item.shiny:
        passes_filter = True

    # Handle PICKUPS with simple boolean config values.
    if loot_type == LootType.PICKUPS:
        if item.pickup_type == PickupType.UNKNOWN:
            warning(f"Unknown pickup type for item: {item}")
            return unknown
        # Ammo is a special case where we want to filter by weapon type as well.
        if item.pickup_type == PickupType.AMMO:
            if item.weapon_type == WeaponType.UNKNOWN:
                warning(f"Unknown weapon type for ammo item: {item}")
                return unknown
            ammo_config = FilterConfig["PICKUPS"]["AMMO"].get(item.weapon_type.name, None)
            if ammo_config is None:
                warning(f"No ammo filter found for weapon type {item.weapon_type}")
                return unknown
            passes_filter = ammo_config.value
        else:
            pickup_config = FilterConfig["PICKUPS"].get(item.pickup_type.name, None)
            if pickup_config is None:
                warning(f"No pickup filter found for pickup type {item.pickup_type}")
                return unknown
            passes_filter = pickup_config.value

    # Handle GEAR by rarity and item type
    if loot_type == LootType.GEAR:
        rarity = item.rarity
        if rarity == Rarity.UNKNOWN:
            warning(f"Unknown rarity for item: {item}")
            return unknown
        rarity_config = CONFIG.get("GEAR", {}).get(rarity.name, {})

        match item.item_type:
            case ItemType.WEAPON:
                if item.weapon_type == WeaponType.UNKNOWN:
                    warning(f"Unknown weapon type for item: {item}")
                    return unknown
                if item.manufacturer == Manufacturer.UNKNOWN:
                    warning(f"Unknown manufacturer for item: {item}")
                    return unknown
                passes_filter = bool(rarity_config
                            .get("WEAPON", {})
                            .get(item.weapon_type.name, {})
                            .get(item.manufacturer.name, False))
            case (ItemType.SHIELD | ItemType.GRENADE | ItemType.HEAVY_ORDNANCE |
                  ItemType.REPKIT | ItemType.ENHANCEMENT):
                if item.manufacturer == Manufacturer.UNKNOWN:
                    warning(f"Unknown manufacturer for item: {item}")
                    return unknown
                passes_filter = bool(rarity_config
                            .get(item.item_type.name, {})
                            .get(item.manufacturer.name, False))
            case ItemType.CLASS_MOD:
                if item.vault_hunter == VaultHunter.UNKNOWN:
                    warning(f"Unknown vault hunter for item: {item}")
                    return unknown
                passes_filter = bool(rarity_config
                            .get("CLASS_MOD", {})
                            .get(item.vault_hunter.name, False))
            case ItemType.UNKNOWN:
                warning(f"Unknown item type for item: {item}")
                return unknown

        # Final check to see if it's an item with firmware
        # that we should take regardless of other filters.
        if not passes_filter and item.firmware:
            firmware_filter = FilterConfig["FIRMWARE"].get(item.item_type)
            if firmware_filter is None:
                warning(f"Item has firmware but no firmware filter found for"
                        f"item type {item.item_type} in item: {item}")
                return unknown
            passes_filter = bool(
                firmware_filter.value
            )

    return not unknown and passes_filter != unwanted

DELETE_LOOT_LOCATION = make_struct("Vector", X=100000,Y=100000,Z=-1000000000)
@keybind("Delete Loot")
def delete_loot():
    """Delete only loot that does not pass filter_loot."""
    info("Deleting loot")
    _teleport_loot(DELETE_LOOT_LOCATION, IGNORE_STRUCT, unwanted=True)

@keybind("Teleport Loot")
def teleport_loot():
    """Teleport filtered loot to a location in front of the player."""
    info("Teleporting loot")
    _teleport_loot(*_calculate_teleport_location())

@keybind("Teleport Unknown Loot")
def teleport_unknown_loot():
    """Teleport filtered loot to a location in front of the player."""
    info("Teleporting unknown loot")
    _teleport_loot(*_calculate_teleport_location(backwards=True), unknown=True)

def _calculate_teleport_location(backwards: bool = False):
    """Calculate location to teleport loot to based on player location and rotation,
    so it goes in front of them."""
    player_location = get_pc().Pawn.K2_GetActorLocation()
    player_rot = get_pc().Pawn.K2_GetActorRotation()
    yaw_rad = math.radians(player_rot.Yaw)

    forward_x = math.cos(yaw_rad)
    forward_y = math.sin(yaw_rad)

    offset_x = forward_x * TELEPORT_DISTANCE
    offset_y = forward_y * TELEPORT_DISTANCE
    # Move things up a bit to avoid clipping into geometry.
    offset_z = -40

    if backwards:
        offset_x *= -1
        offset_y *= -1

    new_x = player_location.X + offset_x
    new_y = player_location.Y + offset_y
    new_z = player_location.Z + offset_z

    return make_struct("Vector", X=new_x, Y=new_y, Z=new_z), player_rot

def _teleport_loot(location, rotation, unwanted: bool = False, unknown: bool = False):
    filtered_loot = [i for i in get_loot() if filter_loot(
        LootInfo.from_inventory_pickup(i), unwanted=unwanted, unknown=unknown)]
    for drop in filtered_loot:
        drop.RootPrimitiveComponent.SetSimulatePhysics(True)
        drop.K2_TeleportTo(location, rotation)

build_mod(
    keybinds=[teleport_loot, delete_loot, teleport_unknown_loot],
    options=_populate_filter_config_and_build_options()
)
