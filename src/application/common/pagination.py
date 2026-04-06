from pydantic import BaseModel, ConfigDict

from src.database.psql.types import OrderBy


class OffsetPagination(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_by: OrderBy = "desc"
    offset: int = 0
    limit: int | None = None
