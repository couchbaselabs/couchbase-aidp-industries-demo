"""Small shared helpers used by every industry module's KPI/agent code."""
from typing import Any, Callable, List, Optional


def top_by(entities: List[dict], key: Callable[[dict], float], reverse: bool = True) -> Optional[dict]:
    if not entities:
        return None
    return sorted(entities, key=key, reverse=reverse)[0]


def count_where(entities: List[dict], predicate: Callable[[dict], bool]) -> int:
    return sum(1 for e in entities if predicate(e))


def avg(entities: List[dict], key: Callable[[dict], float]) -> float:
    if not entities:
        return 0.0
    return sum(key(e) for e in entities) / len(entities)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
