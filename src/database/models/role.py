from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm

from src.common.tools.text import pascal_to_snake
from src.database.models import Base, types
from src.database.models.base import mixins

if TYPE_CHECKING:
    from src.database.models import User


class Role(mixins.UUIDMixin, mixins.TimeMixin, Base):
    name: orm.Mapped[types.RoleTypeEnum] = orm.mapped_column(
        sa.Enum(
            types.RoleTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
            name=pascal_to_snake(types.RoleTypeEnum),
        ),
        index=True,
    )

    users: orm.Mapped[list["User"]] = orm.relationship(
        "User",
        back_populates="role",
        primaryjoin="Role.uuid == foreign(User.role_uuid)",
    )
