from sqlalchemy import Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, declarative_mixin, mapped_column
from uuid_utils.compat import UUID as uuid_type
from uuid_utils.compat import uuid4


@declarative_mixin
class IDMixin(MappedAsDataclass, init=False):
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )


@declarative_mixin
class UUIDMixin:
    uuid: Mapped[uuid_type] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )
