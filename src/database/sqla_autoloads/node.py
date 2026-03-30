from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar, final

from sqlalchemy import orm

from .datastructures import frozendict


@final
class Node:
    """Singleton class for managing SQLAlchemy model relationship mappings.

    This class stores and provides access to relationship mappings between
    SQLAlchemy models. It implements the singleton pattern to ensure a single
    source of truth for relationship information across the application.

    The Node class is used internally by sqla_select to traverse relationship
    paths and construct appropriate joins and load strategies.
    """

    __instance: ClassVar[Node | None] = None
    _node: Mapping[
        type[orm.DeclarativeBase],
        Sequence[orm.RelationshipProperty[orm.DeclarativeBase]],
    ]

    def __new__(
        cls,
        node: Mapping[
            type[orm.DeclarativeBase],
            Sequence[orm.RelationshipProperty[orm.DeclarativeBase]],
        ]
        | None = None,
    ) -> Node:
        if cls.__instance is None:
            instance = super().__new__(cls)
            if node is not None:
                instance.set_node(node)

            cls.__instance = instance

        if not getattr(cls.__instance, "_node", None):
            raise RuntimeError("Node is not initialized or empty")

        return cls.__instance

    def get(
        self, model: type[orm.DeclarativeBase]
    ) -> Sequence[orm.RelationshipProperty[orm.DeclarativeBase]]:
        """Get relationships for a model, returning empty sequence if not found.

        Args:
            model: SQLAlchemy model class.

        Returns:
            Sequence of relationship properties for the model.
        """
        return self.node.get(model, ())

    def __getitem__(
        self, model: type[orm.DeclarativeBase]
    ) -> Sequence[orm.RelationshipProperty[orm.DeclarativeBase]]:
        return self.node[model]

    @property
    def node(
        self,
    ) -> Mapping[
        type[orm.DeclarativeBase],
        Sequence[orm.RelationshipProperty[orm.DeclarativeBase]],
    ]:
        return self._node

    def set_node(
        self,
        node: Mapping[
            type[orm.DeclarativeBase],
            Sequence[orm.RelationshipProperty[orm.DeclarativeBase]],
        ],
    ) -> None:
        """Set the relationship mapping for this node instance.

        Args:
            node: Mapping from model classes to their relationship properties.
        """
        self._node = node


def get_node(
    base: type[orm.DeclarativeBase],
) -> Mapping[
    type[orm.DeclarativeBase], Sequence[orm.RelationshipProperty[orm.DeclarativeBase]]
]:
    """Extract relationship mappings from a SQLAlchemy declarative base.

    This function introspects all mappers in the registry of the provided base
    class and creates a mapping of model classes to their relationships.

    Args:
        base: SQLAlchemy declarative base class.

    Returns:
        Frozen dictionary mapping model classes to their relationship properties.

    Raises:
        AssertionError: If base is not a subclass of orm.DeclarativeBase.
    """
    assert orm.DeclarativeBase in base.__bases__, (
        "base must be a subclass of orm.DeclarativeBase"
    )

    return frozendict(
        {
            mapper.class_: tuple(mapper.relationships.values())
            for mapper in base.registry.mappers
        }
    )


def init_node(
    node: Mapping[
        type[orm.DeclarativeBase],
        Sequence[orm.RelationshipProperty[orm.DeclarativeBase]],
    ],
) -> None:
    """Initialize the global Node singleton with relationship mappings.

    This function creates or updates the singleton Node instance with the
    provided relationship mappings. It should be called once during application
    startup to set up the relationship graph.

    Args:
        node: Mapping from model classes to their relationship properties.

    Example:
        >>> from myapp.models import Base
        >>> node_mapping = get_node(Base)
        >>> init_node(node_mapping)
    """
    Node(node)
