from __future__ import annotations

import json
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_assistant.survey.mission_state import MissionStateError, canonical_json_bytes, sha256_bytes


STRATEGY_SCHEMA = "ra-survey-topic-query-strategy-v2"
STRATEGY_ROOT = Path(__file__).with_name("strategies")
GENERIC_STRATEGY_FILE = STRATEGY_ROOT / "generic_topic.json"
STRATEGY_FILE = GENERIC_STRATEGY_FILE
ALLOWED_SORTS = {"cited_by_count:desc", "publication_date:desc"}
ALLOWED_ELIGIBILITY_POLICIES = {
    "all_required_topic_groups",
    "minimum_topic_token_match",
}
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")


def _fail(message: str) -> None:
    raise MissionStateError("invalid_topic_query_strategy", message)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        _fail(f"{field} must be nonempty text")
    return " ".join(value.split())


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        _fail(f"{field} must be a nonempty list")
    result = [_text(item, f"{field}[]").casefold() for item in value]
    if result != sorted(set(result)):
        _fail(f"{field} must be unique and sorted")
    return result


@dataclass(frozen=True)
class QueryLayer:
    kind: str
    purpose: str
    priority: int
    filter: str
    sort: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "purpose": self.purpose,
            "priority": self.priority,
            "filter": self.filter,
            "sort": self.sort,
        }


@dataclass(frozen=True)
class QueryStrategy:
    profile_id: str
    profile_version: int
    eligibility_policy: str
    required_topic_groups: dict[str, tuple[str, ...]]
    selected_seed_cap: int
    strategy_nonclaims: tuple[str, ...]
    strata: tuple[QueryLayer, ...]
    sha256: str


class QueryPlanner:
    def __init__(self, strategy: QueryStrategy) -> None:
        self.strategy = strategy

    def plan(self, *, max_requests: int) -> tuple[QueryLayer, ...]:
        if len(self.strategy.strata) > max_requests:
            _fail("query strategy exceeds the mission request budget")
        return self.strategy.strata


def validate_strategy(value: Any) -> dict[str, Any]:
    expected = {
        "profile_id",
        "profile_version",
        "eligibility_policy",
        "required_topic_groups",
        "selected_seed_cap",
        "strategy_nonclaims",
        "strata",
    }
    if not isinstance(value, dict) or set(value) != expected:
        _fail("strategy fields are not exact")
    profile_id = _text(value["profile_id"], "profile_id").casefold()
    if _IDENTIFIER.fullmatch(profile_id) is None:
        _fail("profile_id must be a lowercase identifier")
    version = value["profile_version"]
    eligibility_policy = _text(value["eligibility_policy"], "eligibility_policy").casefold()
    selected_cap = value["selected_seed_cap"]
    if type(version) is not int or version <= 0:
        _fail("profile_version must be a positive integer")
    if eligibility_policy not in ALLOWED_ELIGIBILITY_POLICIES:
        _fail("eligibility_policy is unsupported")
    if type(selected_cap) is not int or not 1 <= selected_cap <= 12:
        _fail("selected_seed_cap must be in [1, 12]")
    groups = value["required_topic_groups"]
    if not isinstance(groups, dict) or not groups:
        _fail("required_topic_groups must be a nonempty object")
    if any(
        not isinstance(key, str)
        or key != key.casefold()
        or _IDENTIFIER.fullmatch(key) is None
        for key in groups
    ):
        _fail("required_topic_groups keys must be lowercase identifiers")
    normalized_groups = {key: _string_list(groups[key], f"required_topic_groups.{key}") for key in sorted(groups)}
    nonclaims = _string_list(value["strategy_nonclaims"], "strategy_nonclaims")
    strata = value["strata"]
    if not isinstance(strata, list) or not strata:
        _fail("strata must be a nonempty list")
    normalized_strata: list[dict[str, Any]] = []
    kinds: set[str] = set()
    priorities: set[int] = set()
    for index, row in enumerate(strata):
        field = f"strata[{index}]"
        if not isinstance(row, dict) or set(row) != {"kind", "purpose", "priority", "filter", "sort"}:
            _fail(f"{field} fields are not exact")
        kind = _text(row["kind"], f"{field}.kind").casefold()
        purpose = _text(row["purpose"], f"{field}.purpose").casefold()
        query_filter = _text(row["filter"], f"{field}.filter")
        sort = _text(row["sort"], f"{field}.sort")
        priority = row["priority"]
        if _IDENTIFIER.fullmatch(kind) is None or _IDENTIFIER.fullmatch(purpose) is None:
            _fail(f"{field} kind and purpose must be lowercase identifiers")
        if sort not in ALLOWED_SORTS:
            _fail(f"{field} sort is unsupported")
        if type(priority) is not int or priority <= 0 or kind in kinds or priority in priorities:
            _fail(f"{field} kind or priority is invalid or duplicated")
        if not query_filter.startswith("title.search:"):
            _fail(f"{field}.filter must use bounded title.search terms")
        kinds.add(kind)
        priorities.add(priority)
        normalized_strata.append({
            "kind": kind,
            "purpose": purpose,
            "priority": priority,
            "filter": query_filter,
            "sort": sort,
        })
    normalized_strata.sort(key=lambda row: (row["priority"], row["kind"]))
    if [row["priority"] for row in normalized_strata] != list(range(1, len(normalized_strata) + 1)):
        _fail("stratum priorities must be contiguous from one")
    return {
        "profile_id": profile_id,
        "profile_version": version,
        "eligibility_policy": eligibility_policy,
        "required_topic_groups": normalized_groups,
        "selected_seed_cap": selected_cap,
        "strategy_nonclaims": nonclaims,
        "strata": normalized_strata,
    }


def load_strategy(path: Path = STRATEGY_FILE) -> QueryStrategy:
    path = path.resolve(strict=True)
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        _fail("strategy must be a regular non-symlink file")
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionStateError("invalid_topic_query_strategy", "strategy is not valid JSON") from exc
    normalized = validate_strategy(value)
    normalized_raw = canonical_json_bytes(normalized)
    return QueryStrategy(
        profile_id=normalized["profile_id"],
        profile_version=normalized["profile_version"],
        eligibility_policy=normalized["eligibility_policy"],
        required_topic_groups={key: tuple(values) for key, values in normalized["required_topic_groups"].items()},
        selected_seed_cap=normalized["selected_seed_cap"],
        strategy_nonclaims=tuple(normalized["strategy_nonclaims"]),
        strata=tuple(QueryLayer(**row) for row in normalized["strata"]),
        sha256=sha256_bytes(normalized_raw),
    )


__all__ = [
    "ALLOWED_ELIGIBILITY_POLICIES",
    "QueryLayer",
    "QueryPlanner",
    "QueryStrategy",
    "GENERIC_STRATEGY_FILE",
    "STRATEGY_FILE",
    "STRATEGY_SCHEMA",
    "load_strategy",
    "validate_strategy",
]
