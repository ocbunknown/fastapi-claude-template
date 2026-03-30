from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm

from src.database.models import Base
from src.database.models.base import mixins

if TYPE_CHECKING:
    from src.database.models import Role


class User(mixins.UUIDMixin, mixins.TimeMixin, Base):
    login: orm.Mapped[str] = orm.mapped_column(
        sa.String, index=True, unique=True, nullable=False
    )
    password: orm.Mapped[str] = orm.mapped_column(sa.String, nullable=False)
    active: orm.Mapped[bool] = orm.mapped_column(
        sa.Boolean, default=True, index=True, nullable=False
    )

    role_uuid: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(True),
        sa.ForeignKey("role.uuid", ondelete="RESTRICT", name="fk_user_role"),
    )

    role: orm.Mapped[Role] = orm.relationship(
        "Role",
        back_populates="users",
        primaryjoin="User.role_uuid == Role.uuid",
    )
