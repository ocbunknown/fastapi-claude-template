from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, Self


class frozendict[K, V](Mapping[K, V]):  # noqa: N801
    """Immutable dictionary implementation with hash support.

    This class provides a hashable, immutable dictionary that can be used
    as keys in other dictionaries or stored in sets. It implements the
    Mapping protocol and maintains the same interface as a regular dict
    for read operations.

    The frozendict is used internally for caching purposes and ensuring
    immutability of configuration parameters.

    Example:
        >>> fd = frozendict({"a": 1, "b": 2})
        >>> fd["a"]
        1
        >>> hash(fd)  # This works unlike regular dict
        -1234567890
        >>> fd2 = fd.copy(c=3)  # Create new instance with additional items
        >>> fd2
        <frozendict {'a': 1, 'b': 2, 'c': 3}>
    """

    __slots__ = ("_dict", "_hash")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._dict: dict[K, V] = dict(*args, **kwargs)
        self._hash = hash(frozenset(self._dict.items()))

    def __getitem__(self, key: K) -> V:
        return self._dict[key]

    def __contains__(self, key: Any) -> bool:
        return key in self._dict

    def copy(self, **add_or_replace: Any) -> Self:
        """Create a new frozendict with additional or replaced items.

        Args:
            **add_or_replace: Keyword arguments for items to add or replace.

        Returns:
            New frozendict instance with the merged items.
        """
        return type(self)(self, **add_or_replace)

    def __iter__(self) -> Iterator[K]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._dict!r}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, frozendict):
            return self._dict == other._dict

        if isinstance(other, dict):
            return self._dict == other

        return NotImplemented

    def __hash__(self) -> int:
        return self._hash
