from .base import inject
from .container import container
from .marker import Depends, FromDepends

__all__ = ("container", "Depends", "FromDepends", "inject")
