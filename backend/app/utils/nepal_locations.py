import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

LOCATIONS_FILE = Path(__file__).parent.parent.parent / "nepal_admin_structure_province_names.json"


@lru_cache(maxsize=1)
def load_locations() -> Dict:
    """Load Nepal administrative structure from JSON file (cached for the process lifetime)."""
    try:
        with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_provinces() -> List[str]:
    """Get all provinces"""
    locations = load_locations()
    return sorted(list(locations.keys()))


def get_districts(province: str) -> List[str]:
    """Get all districts for a province"""
    locations = load_locations()
    if province not in locations:
        return []
    return sorted(list(locations[province].keys()))


def get_municipalities(province: str, district: str) -> List[Dict]:
    """Get all municipalities (local levels) for a province/district with ward counts"""
    locations = load_locations()
    if province not in locations or district not in locations[province]:
        return []
    return locations[province][district]


def get_wards(province: str, district: str, municipality: str) -> int:
    """Get number of wards for a municipality"""
    municipalities = get_municipalities(province, district)
    for muni in municipalities:
        if muni['local_level_name'] == municipality:
            return muni.get('wards', 0)
    return 0
