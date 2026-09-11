"""Registry of every industry vertical the demo operator can choose from."""
from typing import Dict, List

from app.industries import (
    banking,
    energy,
    healthcare,
    manufacturing,
    media,
    public_sector,
    retail,
    saas,
    telecom,
    travel,
)
from app.industries.base import Industry

_REGISTRY: Dict[str, Industry] = {
    mod.INDUSTRY.id: mod.INDUSTRY
    for mod in (retail, banking, telecom, healthcare, travel, media, saas, manufacturing, energy, public_sector)
}


def list_industries() -> List[Industry]:
    return list(_REGISTRY.values())


def get_industry(industry_id: str) -> Industry:
    try:
        return _REGISTRY[industry_id]
    except KeyError as exc:
        raise KeyError(f"Unknown industry '{industry_id}'") from exc
