from typing import Sequence, Union

from alembic import op

revision: str = "02_82e484eb7a8e"
down_revision: Union[str, None] = "01_3d1a9bc30546"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_user_login", table_name="user")
    op.create_index(op.f("ix_user_login"), "user", ["login"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_login"), table_name="user")
    op.create_index("ix_user_login", "user", ["login"], unique=False)
