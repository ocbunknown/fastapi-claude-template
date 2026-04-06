from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.common.pagination import OffsetPagination as AppOffsetPagination
from src.presentation.http.v1.contracts.pagination import (
    MAX_PAGINATION_LIMIT,
    MIN_PAGINATION_LIMIT,
)
from src.presentation.http.v1.contracts.pagination import (
    OffsetPagination as ContractOffsetPagination,
)


class TestContractOffsetPagination:
    """Strict — public HTTP-facing pagination."""

    def test_defaults(self) -> None:
        pag = ContractOffsetPagination()

        assert pag.order_by == "desc"
        assert pag.offset == 0
        assert pag.limit == MIN_PAGINATION_LIMIT

    def test_accepts_limit_within_bounds(self) -> None:
        for limit in (MIN_PAGINATION_LIMIT, 50, 100, MAX_PAGINATION_LIMIT):
            pag = ContractOffsetPagination(limit=limit)
            assert pag.limit == limit

    @pytest.mark.parametrize("bad_limit", [-1, 0, 1, 9])
    def test_rejects_limit_below_min(self, bad_limit: int) -> None:
        with pytest.raises(ValidationError) as exc:
            ContractOffsetPagination(limit=bad_limit)
        assert "greater than or equal" in str(exc.value)

    @pytest.mark.parametrize("bad_limit", [201, 500, 10_000])
    def test_rejects_limit_above_max(self, bad_limit: int) -> None:
        with pytest.raises(ValidationError) as exc:
            ContractOffsetPagination(limit=bad_limit)
        assert "less than or equal" in str(exc.value)

    def test_rejects_negative_offset(self) -> None:
        with pytest.raises(ValidationError):
            ContractOffsetPagination(offset=-1)

    def test_accepts_zero_offset(self) -> None:
        pag = ContractOffsetPagination(offset=0)
        assert pag.offset == 0

    def test_order_by_accepts_asc_and_desc(self) -> None:
        assert ContractOffsetPagination(order_by="asc").order_by == "asc"
        assert ContractOffsetPagination(order_by="desc").order_by == "desc"

    def test_order_by_rejects_unknown(self) -> None:
        with pytest.raises(ValidationError):
            ContractOffsetPagination(order_by="random")  # type: ignore[arg-type]


class TestApplicationOffsetPagination:
    """Lenient — internal/use-case input, supports unbounded fetch."""

    def test_defaults_to_unlimited(self) -> None:
        pag = AppOffsetPagination()

        assert pag.order_by == "desc"
        assert pag.offset == 0
        assert pag.limit is None

    def test_accepts_none_limit(self) -> None:
        pag = AppOffsetPagination(limit=None)
        assert pag.limit is None

    @pytest.mark.parametrize("limit", [1, 10, 200, 5_000, 100_000])
    def test_accepts_arbitrary_positive_limit(self, limit: int) -> None:
        pag = AppOffsetPagination(limit=limit)
        assert pag.limit == limit

    def test_is_frozen(self) -> None:
        pag = AppOffsetPagination(offset=10)
        with pytest.raises(ValidationError):
            pag.offset = 20  # type: ignore[misc]


class TestContractToApplicationMapping:
    """Endpoint maps strict contract → lenient application instance."""

    def test_round_trip_via_model_dump(self) -> None:
        contract = ContractOffsetPagination(order_by="asc", offset=20, limit=50)

        app = AppOffsetPagination(**contract.model_dump())

        assert app.order_by == "asc"
        assert app.offset == 20
        assert app.limit == 50

    def test_default_contract_maps_to_finite_limit(self) -> None:
        # Important: when contract is used (HTTP path), the resulting
        # application pagination has a real int limit, never None.
        contract = ContractOffsetPagination()
        app = AppOffsetPagination(**contract.model_dump())

        assert app.limit == MIN_PAGINATION_LIMIT
        assert app.limit is not None
