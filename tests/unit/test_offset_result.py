from __future__ import annotations

import uuid_utils.compat as uuid

from src.application.v1.results import OffsetResult, UserResult
from src.application.v1.results.role import RoleResult
from src.presentation.http.v1 import contracts


def _user_result(login: str = "alice") -> UserResult:
    return UserResult(
        uuid=uuid.uuid4(),
        login=login,
        active=True,
        role=RoleResult(uuid=uuid.uuid4(), name="Admin"),
    )


def test_map_converts_each_item_via_callable() -> None:
    src = OffsetResult[UserResult](
        data=[_user_result("alice"), _user_result("bob")],
        offset=20,
        limit=50,
        total=42,
    )

    mapped = src.map(contracts.User.model_validate)

    assert len(mapped.data) == 2
    assert all(isinstance(u, contracts.User) for u in mapped.data)
    assert [u.login for u in mapped.data] == ["alice", "bob"]


def test_map_preserves_offset_limit_total() -> None:
    src = OffsetResult[UserResult](
        data=[_user_result()], offset=20, limit=50, total=42
    )

    mapped = src.map(contracts.User.model_validate)

    assert mapped.offset == 20
    assert mapped.limit == 50
    assert mapped.total == 42


def test_map_preserves_none_limit() -> None:
    src = OffsetResult[UserResult](data=[_user_result()], total=1)

    mapped = src.map(contracts.User.model_validate)

    assert mapped.limit is None
    assert mapped.offset == 0
    assert mapped.total == 1


def test_map_handles_empty_data() -> None:
    src = OffsetResult[UserResult](data=[], offset=0, limit=10, total=0)

    mapped = src.map(contracts.User.model_validate)

    assert mapped.data == []
    assert mapped.total == 0
    assert mapped.limit == 10


def test_map_propagates_nested_role_via_from_attributes() -> None:
    src = OffsetResult[UserResult](data=[_user_result()], total=1)

    mapped = src.map(contracts.User.model_validate)

    assert mapped.data[0].role is not None
    assert mapped.data[0].role.name == "Admin"


def test_map_does_not_mutate_source() -> None:
    src = OffsetResult[UserResult](
        data=[_user_result(), _user_result()], offset=0, limit=10, total=2
    )

    src.map(contracts.User.model_validate)

    # Source items remain UserResult, not contracts.User
    assert all(isinstance(item, UserResult) for item in src.data)
