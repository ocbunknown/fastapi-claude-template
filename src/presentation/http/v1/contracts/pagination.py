from typing import Annotated, Final

from pydantic import Field

from src.database.psql.types import OrderBy
from src.presentation.http.common.contract import Contract

MIN_PAGINATION_LIMIT: Final[int] = 10
MAX_PAGINATION_LIMIT: Final[int] = 200


class OffsetPagination(Contract):
    order_by: OrderBy = "desc"
    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[
        int,
        Field(ge=MIN_PAGINATION_LIMIT, le=MAX_PAGINATION_LIMIT),
    ] = MIN_PAGINATION_LIMIT
