from sqla_autoloads import get_node, init_node

from .base import Base
from .role import Role
from .user import User

__all__ = ("Base", "User", "Role")


init_node(get_node(Base))
