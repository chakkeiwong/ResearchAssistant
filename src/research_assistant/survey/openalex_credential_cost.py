from __future__ import annotations

import hashlib
import json
import math
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from research_assistant.survey.mission_state import (
    MissionStateError,
    canonical_json_bytes,
)
from research_assistant.survey.openalex_adapter import (
    parse_openalex_direct_response,
    parse_openalex_forward_response,
    parse_openalex_topic_response,
    validate_openalex_descriptor,
)


CREDENTIAL_INTERFACE = "OPENALEX_API_KEY"
CREDENTIAL_SOURCE_KIND = "environment"
CAMPAIGN_COST_CAP_USD = Decimal("0.01")
ROUTE_COST_USD = {
    "topic_list": Decimal("0.001"),
    "direct_singleton": Decimal("0"),
    "forward_list": Decimal("0.0001"),
}
EVIDENCE_SCHEMA = "ra-survey-m20b2-openalex-credential-cost-evidence-v1"


class CredentialCostBoundaryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _usd(value: Decimal) -> str:
    return format(value, "f")


def _decimal_usd(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise CredentialCostBoundaryError("invalid_observed_cost")
    if isinstance(value, float) and not math.isfinite(value):
        raise CredentialCostBoundaryError("invalid_observed_cost")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise CredentialCostBoundaryError("invalid_observed_cost") from exc
    if not parsed.is_finite() or parsed < 0:
        raise CredentialCostBoundaryError("invalid_observed_cost")
    return parsed


@dataclass(frozen=True)
class _BudgetStateToken:
    cap_usd: Decimal
    reserved_usd: Decimal
    reconciled_usd: Decimal
    dispatch_count: int
    blocked: bool
    block_code: str | None
    dispatch_in_flight: bool
    version: int


@dataclass(frozen=True)
class _CostReservation:
    route_kind: str
    predicted_usd: Decimal
    state: _BudgetStateToken


@dataclass(frozen=True)
class _DispatchedReservation:
    route_kind: str
    predicted_usd: Decimal
    state: _BudgetStateToken


class CampaignCostBudget:
    def __init__(self, cap_usd: Decimal = CAMPAIGN_COST_CAP_USD) -> None:
        try:
            parsed_cap = Decimal(str(cap_usd))
        except InvalidOperation as exc:
            raise CredentialCostBoundaryError("invalid_campaign_cost_cap") from exc
        if not parsed_cap.is_finite() or parsed_cap != CAMPAIGN_COST_CAP_USD:
            raise CredentialCostBoundaryError("campaign_cost_cap_differs")

        self._lock = threading.RLock()
        self._cap_usd = parsed_cap
        self._reserved_usd = Decimal("0")
        self._reconciled_usd = Decimal("0")
        self._dispatch_count = 0
        self._blocked = False
        self._block_code: str | None = None
        self._dispatch_in_flight = False
        self._version = 0

    @property
    def cap_usd(self) -> Decimal:
        return self._cap_usd

    @property
    def reserved_usd(self) -> Decimal:
        return self._reserved_usd

    @property
    def reconciled_usd(self) -> Decimal:
        return self._reconciled_usd

    @property
    def dispatch_count(self) -> int:
        return self._dispatch_count

    @property
    def blocked(self) -> bool:
        return self._blocked

    @property
    def block_code(self) -> str | None:
        return self._block_code

    def _state_token_locked(self) -> _BudgetStateToken:
        return _BudgetStateToken(
            cap_usd=self._cap_usd,
            reserved_usd=self._reserved_usd,
            reconciled_usd=self._reconciled_usd,
            dispatch_count=self._dispatch_count,
            blocked=self._blocked,
            block_code=self._block_code,
            dispatch_in_flight=self._dispatch_in_flight,
            version=self._version,
        )

    def _validate_locked(self) -> None:
        decimal_fields = (self._cap_usd, self._reserved_usd, self._reconciled_usd)
        if any(not isinstance(value, Decimal) or not value.is_finite() for value in decimal_fields):
            raise CredentialCostBoundaryError("invalid_cost_state")
        if self._cap_usd != CAMPAIGN_COST_CAP_USD:
            raise CredentialCostBoundaryError("invalid_cost_state")
        if self._reserved_usd < 0 or self._reconciled_usd < 0:
            raise CredentialCostBoundaryError("invalid_cost_state")
        if self._reconciled_usd > self._reserved_usd or self._reserved_usd > self._cap_usd:
            raise CredentialCostBoundaryError("invalid_cost_state")
        if isinstance(self._dispatch_count, bool) or not isinstance(self._dispatch_count, int):
            raise CredentialCostBoundaryError("invalid_cost_state")
        if self._dispatch_count < 0:
            raise CredentialCostBoundaryError("invalid_cost_state")
        if not isinstance(self._blocked, bool):
            raise CredentialCostBoundaryError("invalid_cost_state")
        if self._blocked != (isinstance(self._block_code, str) and bool(self._block_code)):
            raise CredentialCostBoundaryError("invalid_cost_state")
        if not isinstance(self._dispatch_in_flight, bool):
            raise CredentialCostBoundaryError("invalid_cost_state")
        if not self._blocked and not self._dispatch_in_flight and self._reserved_usd != self._reconciled_usd:
            raise CredentialCostBoundaryError("invalid_cost_state")
        if isinstance(self._version, bool) or not isinstance(self._version, int) or self._version < 0:
            raise CredentialCostBoundaryError("invalid_cost_state")

    def predicted_cost(self, route_kind: str) -> Decimal:
        try:
            return ROUTE_COST_USD[route_kind]
        except KeyError as exc:
            raise CredentialCostBoundaryError("unknown_route_cost") from exc

    def prepare_reservation(self, route_kind: str) -> _CostReservation:
        with self._lock:
            self._validate_locked()
            if self._blocked:
                raise CredentialCostBoundaryError("campaign_cost_blocked")
            if self._dispatch_in_flight:
                raise CredentialCostBoundaryError("campaign_dispatch_in_flight")
            predicted = self.predicted_cost(route_kind)
            if self._reserved_usd + predicted > self._cap_usd:
                raise CredentialCostBoundaryError("campaign_cost_cap_exceeded")
            return _CostReservation(
                route_kind=route_kind,
                predicted_usd=predicted,
                state=self._state_token_locked(),
            )

    def _mark_dispatched_locked(self, reservation: _CostReservation) -> _DispatchedReservation:
        self._validate_locked()
        if not isinstance(reservation, _CostReservation):
            raise CredentialCostBoundaryError("invalid_cost_reservation")
        if reservation.state != self._state_token_locked():
            raise CredentialCostBoundaryError("cost_state_changed_after_preflight")
        if self._blocked:
            raise CredentialCostBoundaryError("campaign_cost_blocked")
        if reservation.predicted_usd != self.predicted_cost(reservation.route_kind):
            raise CredentialCostBoundaryError("invalid_cost_reservation")
        if self._reserved_usd + reservation.predicted_usd > self._cap_usd:
            raise CredentialCostBoundaryError("campaign_cost_cap_exceeded")
        self._reserved_usd += reservation.predicted_usd
        self._dispatch_count += 1
        self._dispatch_in_flight = True
        self._version += 1
        return _DispatchedReservation(
            route_kind=reservation.route_kind,
            predicted_usd=reservation.predicted_usd,
            state=self._state_token_locked(),
        )

    def mark_dispatched(self, reservation: _CostReservation) -> _DispatchedReservation:
        with self._lock:
            return self._mark_dispatched_locked(reservation)

    @contextmanager
    def dispatch_transaction(self, reservation: _CostReservation):  # noqa: ANN201
        """Hold the budget transaction through dispatch, validation, and evidence."""
        with self._lock:
            dispatched = self._mark_dispatched_locked(reservation)
            yield dispatched

    def block(self, code: str) -> None:
        with self._lock:
            if not isinstance(code, str) or not code:
                code = "invalid_cost_state"
            self._blocked = True
            self._block_code = code
            if isinstance(self._version, int) and not isinstance(self._version, bool) and self._version >= 0:
                self._version += 1

    def reconcile(
        self,
        dispatch: _DispatchedReservation,
        observed_cost_usd: Decimal,
    ) -> None:
        with self._lock:
            self._validate_locked()
            if not isinstance(dispatch, _DispatchedReservation):
                raise CredentialCostBoundaryError("invalid_dispatch_reservation")
            if dispatch.state != self._state_token_locked():
                raise CredentialCostBoundaryError("cost_state_changed_during_dispatch")
            predicted = self.predicted_cost(dispatch.route_kind)
            if dispatch.predicted_usd != predicted:
                raise CredentialCostBoundaryError("invalid_dispatch_reservation")
            if observed_cost_usd != predicted:
                self.block("cost_contradiction")
                raise CredentialCostBoundaryError("cost_contradiction")
            self._reconciled_usd += observed_cost_usd
            if self._reconciled_usd > self._reserved_usd or self._reconciled_usd > self._cap_usd:
                self.block("campaign_cost_cap_exceeded")
                raise CredentialCostBoundaryError("campaign_cost_cap_exceeded")
            self._dispatch_in_flight = False
            self._version += 1

    def evidence(self) -> dict[str, Any]:
        with self._lock:
            try:
                self._validate_locked()
            except CredentialCostBoundaryError:
                return {
                    "campaign_cost_cap_usd": _usd(CAMPAIGN_COST_CAP_USD),
                    "reserved_cost_usd": None,
                    "reconciled_cost_usd": None,
                    "dispatch_count": None,
                    "cost_state": "blocked",
                    "cost_block_code": "invalid_cost_state",
                    "allowance_accounting": "usage_cost_counts_regardless_of_daily_or_prepaid_coverage",
                }
            return {
                "campaign_cost_cap_usd": _usd(self._cap_usd),
                "reserved_cost_usd": _usd(self._reserved_usd),
                "reconciled_cost_usd": _usd(self._reconciled_usd),
                "dispatch_count": self._dispatch_count,
                "cost_state": "blocked" if self._blocked else "open",
                "cost_block_code": self._block_code,
                "allowance_accounting": "usage_cost_counts_regardless_of_daily_or_prepaid_coverage",
            }


def _base_evidence(
    *,
    descriptor: dict[str, Any] | None,
    budget: CampaignCostBudget,
    status: str,
    error_code: str | None,
    predicted_cost: Decimal | None,
    observed_cost: Decimal | None,
    credential_present: bool,
) -> dict[str, Any]:
    route_kind = descriptor["route_kind"] if descriptor is not None else None
    descriptor_sha = hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest() if descriptor is not None else None
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "status": status,
        "error_code": error_code,
        "provider": "openalex",
        "route_kind": route_kind,
        "descriptor_sha256": descriptor_sha,
        "credential_interface": CREDENTIAL_INTERFACE,
        "credential_source_kind": CREDENTIAL_SOURCE_KIND,
        "credential_present": credential_present,
        "credential_persisted": False,
        "authenticated_url_persisted": False,
        "predicted_cost_usd": _usd(predicted_cost) if predicted_cost is not None else None,
        "observed_cost_usd": _usd(observed_cost) if observed_cost is not None else None,
        **budget.evidence(),
    }


def _credential_from_getter(
    getter: Callable[[str], Any],
    *,
    source_kind: str,
) -> str:
    if source_kind != CREDENTIAL_SOURCE_KIND:
        raise CredentialCostBoundaryError("wrong_credential_source")
    try:
        value = getter(CREDENTIAL_INTERFACE)
    except Exception as exc:
        raise CredentialCostBoundaryError("credential_lookup_failed") from exc
    if isinstance(value, (list, tuple, set, dict)):
        raise CredentialCostBoundaryError("ambiguous_credential")
    if not isinstance(value, str) or not value or value != value.strip():
        raise CredentialCostBoundaryError("invalid_credential")
    if len(value) > 4096 or not value.isprintable() or any(char.isspace() for char in value):
        raise CredentialCostBoundaryError("invalid_credential")
    return value


def _request_for_descriptor(descriptor: dict[str, Any], credential: str) -> urllib.request.Request:
    path = "/" + "/".join(urllib.parse.quote(part, safe="") for part in descriptor["path_segments"])
    query = [tuple(item) for item in descriptor["ordered_query_parameters"]]
    query.append(("api_key", credential))
    url = urllib.parse.urlunsplit(("https", descriptor["host"], path, urllib.parse.urlencode(query), ""))
    return urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "research-assistant-m20b2/0.1",
        },
    )


def _loads_json(body: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    return json.loads(
        body.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_float=Decimal,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _validate_response_and_cost(descriptor: dict[str, Any], body: bytes) -> Decimal:
    route_kind = descriptor["route_kind"]
    if route_kind == "topic_list":
        topic = descriptor["ordered_query_parameters"][0][1]
        parse_openalex_topic_response(body, topic=topic)
    elif route_kind == "direct_singleton":
        parse_openalex_direct_response(body, expected_openalex_id=descriptor["path_segments"][1])
        return Decimal("0")
    elif route_kind == "forward_list":
        parse_openalex_forward_response(body)
    else:
        raise CredentialCostBoundaryError("unknown_route_cost")
    try:
        value = _loads_json(body)
        return _decimal_usd(value["meta"]["cost_usd"])
    except (KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CredentialCostBoundaryError("missing_observed_cost") from exc


def _credential_representations(credential: str) -> frozenset[bytes]:
    if not isinstance(credential, str) or not credential:
        raise CredentialCostBoundaryError("invalid_forbidden_value")
    direct = {
        credential,
        urllib.parse.quote(credential, safe=""),
        urllib.parse.quote_plus(credential, safe=""),
        json.dumps(credential, ensure_ascii=True)[1:-1],
    }
    representations = direct | {
        json.dumps(value, ensure_ascii=True)[1:-1]
        for value in direct
    }
    return frozenset(value.encode("utf-8") for value in representations)


def contains_credential_representation(raw: bytes, credential: str) -> bool:
    if not isinstance(raw, bytes):
        raise CredentialCostBoundaryError("invalid_scan_candidate")
    return any(value in raw for value in _credential_representations(credential))


def _value_contains_credential_representation(value: Any, credential: str) -> bool:
    if isinstance(value, str):
        return contains_credential_representation(value.encode("utf-8"), credential)
    if isinstance(value, bytes):
        return contains_credential_representation(value, credential)
    if isinstance(value, dict):
        return any(
            _value_contains_credential_representation(key, credential)
            or _value_contains_credential_representation(item, credential)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_value_contains_credential_representation(item, credential) for item in value)
    return False


def serialize_boundary_evidence(evidence: Any, *, forbidden_value: str) -> bytes:
    """Serialize only closed evidence; reject any value containing credential bytes."""

    if _value_contains_credential_representation(evidence, forbidden_value):
        raise CredentialCostBoundaryError("credential_in_ipc_candidate")
    try:
        raw = canonical_json_bytes(evidence)
    except MissionStateError as exc:
        raise CredentialCostBoundaryError("evidence_serialization_failed") from exc
    if contains_credential_representation(raw, forbidden_value):
        raise CredentialCostBoundaryError("credential_in_ipc_candidate")
    return raw


def execute_authenticated_openalex_request(
    descriptor_value: Any,
    *,
    credential_getter: Callable[[str], Any],
    credential_source_kind: str,
    dispatch: Callable[[urllib.request.Request], bytes],
    budget: CampaignCostBudget,
) -> tuple[bytes | None, dict[str, Any]]:
    """Execute one bounded request without allowing credential-bearing state to escape."""

    if not isinstance(budget, CampaignCostBudget):
        closed_budget = CampaignCostBudget()
        closed_budget.block("invalid_cost_budget")
        return None, _base_evidence(
            descriptor=None,
            budget=closed_budget,
            status="blocked_preflight",
            error_code="invalid_cost_budget",
            predicted_cost=None,
            observed_cost=None,
            credential_present=False,
        )

    descriptor: dict[str, Any] | None = None
    predicted: Decimal | None = None
    reservation: _CostReservation | None = None
    credential_present = False
    try:
        descriptor = validate_openalex_descriptor(descriptor_value)
        reservation = budget.prepare_reservation(descriptor["route_kind"])
        predicted = reservation.predicted_usd
    except (MissionStateError, CredentialCostBoundaryError):
        return None, _base_evidence(
            descriptor=descriptor,
            budget=budget,
            status="blocked_preflight",
            error_code="descriptor_or_cost_preflight_invalid",
            predicted_cost=predicted,
            observed_cost=None,
            credential_present=False,
        )

    try:
        credential = _credential_from_getter(
            credential_getter,
            source_kind=credential_source_kind,
        )
        credential_present = True
    except CredentialCostBoundaryError as exc:
        return None, _base_evidence(
            descriptor=descriptor,
            budget=budget,
            status="blocked_before_dispatch",
            error_code=exc.code,
            predicted_cost=predicted,
            observed_cost=None,
            credential_present=False,
        )

    try:
        request = _request_for_descriptor(descriptor, credential)
    except Exception:
        return None, _base_evidence(
            descriptor=descriptor,
            budget=budget,
            status="blocked_before_dispatch",
            error_code="request_construction_failed",
            predicted_cost=predicted,
            observed_cost=None,
            credential_present=credential_present,
        )

    try:
        with budget.dispatch_transaction(reservation) as dispatched:
            try:
                body = dispatch(request)
            except Exception:
                budget.block("dispatch_cost_unreconciled")
                return None, _base_evidence(
                    descriptor=descriptor,
                    budget=budget,
                    status="blocked_after_dispatch",
                    error_code="dispatch_failed_closed",
                    predicted_cost=predicted,
                    observed_cost=None,
                    credential_present=credential_present,
                )

            if not isinstance(body, bytes):
                budget.block("dispatch_cost_unreconciled")
                return None, _base_evidence(
                    descriptor=descriptor,
                    budget=budget,
                    status="blocked_after_dispatch",
                    error_code="response_type_invalid",
                    predicted_cost=predicted,
                    observed_cost=None,
                    credential_present=credential_present,
                )
            if contains_credential_representation(body, credential):
                budget.block("credential_echoed_in_response")
                return None, _base_evidence(
                    descriptor=descriptor,
                    budget=budget,
                    status="blocked_after_dispatch",
                    error_code="credential_echoed_in_response",
                    predicted_cost=predicted,
                    observed_cost=None,
                    credential_present=credential_present,
                )

            observed: Decimal | None = None
            try:
                observed = _validate_response_and_cost(descriptor, body)
                budget.reconcile(dispatched, observed)
            except (MissionStateError, CredentialCostBoundaryError) as exc:
                current_code = budget.evidence()["cost_block_code"]
                if isinstance(exc, CredentialCostBoundaryError) and exc.code in {
                    "cost_state_changed_during_dispatch",
                    "invalid_cost_state",
                    "invalid_dispatch_reservation",
                }:
                    current_code = exc.code
                    budget.block(current_code)
                elif current_code is None:
                    current_code = "response_cost_unreconciled"
                    budget.block(current_code)
                return None, _base_evidence(
                    descriptor=descriptor,
                    budget=budget,
                    status="blocked_after_dispatch",
                    error_code=current_code,
                    predicted_cost=predicted,
                    observed_cost=observed,
                    credential_present=credential_present,
                )

            return body, _base_evidence(
                descriptor=descriptor,
                budget=budget,
                status="completed",
                error_code=None,
                predicted_cost=predicted,
                observed_cost=observed,
                credential_present=credential_present,
            )
    except CredentialCostBoundaryError as exc:
        error_code = (
            "invalid_cost_state"
            if exc.code == "invalid_cost_state"
            else "cost_state_changed_after_credential_lookup"
        )
        budget.block(error_code)
        return None, _base_evidence(
            descriptor=descriptor,
            budget=budget,
            status="blocked_before_dispatch",
            error_code=error_code,
            predicted_cost=predicted,
            observed_cost=None,
            credential_present=credential_present,
        )



__all__ = [
    "CAMPAIGN_COST_CAP_USD",
    "CREDENTIAL_INTERFACE",
    "CREDENTIAL_SOURCE_KIND",
    "CampaignCostBudget",
    "CredentialCostBoundaryError",
    "ROUTE_COST_USD",
    "contains_credential_representation",
    "execute_authenticated_openalex_request",
    "serialize_boundary_evidence",
]
