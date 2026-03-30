from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache, reduce
from typing import TYPE_CHECKING, Any, Final, Literal, Required, TypedDict, Unpack

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite
from sqlalchemy.orm.util import LoaderCriteriaOption
from sqlalchemy.sql import bindparam, elements, visitors
from sqlalchemy.sql.selectable import LateralFromClause

from .datastructures import frozendict
from .node import Node
from .tools import get_primary_key, get_table_name, get_table_names

if TYPE_CHECKING:
    from sqlalchemy.orm.strategy_options import _AbstractLoad

DEFAULT_RELATIONSHIP_LOAD_LIMIT: Final[int] = 50


@dataclass(slots=True)
class _LoadSelfParams[T: orm.DeclarativeBase]:
    model: type[T]
    relationship: orm.RelationshipProperty[T]
    self_key: str
    order_by: tuple[str, ...] | None = None
    limit: int | None = None
    load: _AbstractLoad | None = None
    conditions: (
        Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
    ) = None

    @classmethod
    def from_relation_params(cls, params: _LoadRelationParams[T]) -> _LoadSelfParams[T]:
        if not params.self_key:
            raise ValueError("`self_key` should be set for self join")

        return cls(
            model=params.model,
            relationship=params.relationship,
            self_key=params.self_key,
            order_by=params.order_by,
            limit=params.limit,
            load=params.load,
            conditions=params.conditions,
        )


@dataclass(slots=True)
class _LoadRelationParams[T: orm.DeclarativeBase]:
    model: type[T]
    relationship: orm.RelationshipProperty[T]
    is_alias: bool = False
    check_tables: bool = False
    order_by: tuple[str, ...] | None = None
    conditions: (
        Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
    ) = None
    load: _AbstractLoad | None = None
    limit: int | None = None
    self_key: str | None = None

    @classmethod
    def from_construct_loads_params(
        cls,
        params: _ConstructLoadsParams[T],
        relationship: orm.RelationshipProperty[T],
        load: _AbstractLoad | None = None,
        *,
        is_alias: bool,
    ) -> _LoadRelationParams[T]:
        return cls(
            model=params.model,
            conditions=params.conditions,
            order_by=params.order_by,
            limit=params.limit,
            self_key=params.self_key,
            check_tables=params.check_tables,
            relationship=relationship,
            load=load,
            is_alias=is_alias,
        )


@dataclass(slots=True)
class _ConstructLoadsParams[T: orm.DeclarativeBase]:
    model: type[T]
    conditions: (
        Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
    ) = None
    order_by: tuple[str, ...] | None = None
    self_key: str | None = None
    limit: int | None = None
    check_tables: bool = False

    @classmethod
    def from_params(cls, params: _LoadParams[T]) -> _ConstructLoadsParams[T]:
        return cls(
            model=params.model,
            conditions=params.conditions,
            order_by=params.order_by,
            self_key=params.self_key,
            limit=params.limit,
            check_tables=params.check_tables,
        )


@dataclass(slots=True, frozen=True)
class _LoadParams[T: orm.DeclarativeBase]:
    model: type[T]
    loads: tuple[str, ...] = ()
    node: Node = field(default_factory=Node)
    limit: int | None = field(default=DEFAULT_RELATIONSHIP_LOAD_LIMIT)
    check_tables: bool = field(default=False)
    distinct: bool = field(default=False)
    conditions: (
        Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
    ) = field(default=None)
    self_key: str | None = field(default=None)
    order_by: tuple[str, ...] | None = field(default=None)
    query: sa.Select[tuple[T]] | None = field(default=None)


class _LoadParamsType[T: orm.DeclarativeBase](TypedDict, total=False):
    model: Required[type[T]]
    node: Node
    check_tables: bool
    conditions: (
        Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
    )
    self_key: str
    order_by: tuple[str, ...]
    query: sa.Select[tuple[T]]
    distinct: bool
    limit: int | None


@lru_cache(maxsize=1028)
def _bfs_search[T: orm.DeclarativeBase](
    start: type[T],
    end: str,
    node: Node,
) -> Sequence[orm.RelationshipProperty[T]]:
    """Perform breadth-first search to find relationship path.

    Searches for a path of relationships from a starting model to a target
    relationship key using breadth-first traversal of the relationship graph.

    Args:
        start: Starting SQLAlchemy model class.
        end: Target relationship key to find.
        node: Node instance containing relationship mappings.

    Returns:
        Sequence of relationship properties forming the path to the target.
    """
    queue: deque[Any] = deque([[start]])
    seen = set()

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current in seen:
            continue
        seen.add(current)

        relations = node.get(current)
        for relation in relations:
            new_path = [*path, relation]

            if relation.key == end:
                return [
                    rel for rel in new_path if isinstance(rel, orm.RelationshipProperty)
                ]

            queue.append([*new_path, relation.mapper.class_])

    return []


def _construct_strategy[T: orm.DeclarativeBase](
    strategy: Callable[..., _AbstractLoad],
    relationship: orm.RelationshipProperty[T],
    current: _AbstractLoad | None = None,
    **kw: Any,
) -> _AbstractLoad:
    _strategy: _AbstractLoad = (
        strategy(relationship, **kw)
        if current is None
        else getattr(current, strategy.__name__)(relationship, **kw)
    )

    return _strategy


def _load_self[T: orm.DeclarativeBase](
    query: sa.Select[tuple[T]],
    params: _LoadSelfParams[T],
    *,
    side: Literal["many", "one"],
) -> tuple[sa.Select[tuple[T]], _AbstractLoad]:
    """Handle loading for self-referential relationships.

    Special handling for relationships where a model references itself,
    creating appropriate aliases and joins to avoid conflicts.

    Args:
        query: SQLAlchemy select query to modify.
        params: Parameters for the self-referential relationship.
        side: Whether this is a "many" or "one" side of the relationship.

    Returns:
        Tuple of modified query and the load strategy.
    """
    (
        load,
        relationship,
        order_by,
        relation_cls,
        limit,
        model,
        self_key,
        conditions,
    ) = (
        params.load,
        params.relationship,
        params.order_by,
        params.relationship.mapper.class_,
        params.limit,
        params.model,
        params.self_key,
        params.conditions or {},
    )
    name = f"{get_table_name(relation_cls)}_{relationship.key}"
    alias: LateralFromClause | type[T]

    alias = orm.aliased(relation_cls, name=name)
    alias_name = f"{name}."
    replace_with = [
        (original_name, alias_name)
        for original_name in _get_possible_quoted_names_for_replacement(model)
    ]

    if side == "many":
        if limit:
            subq = _apply_conditions(
                _apply_order_by(
                    sa.select(alias).limit(limit),
                    relation_cls,
                    order_by,
                ),
                relationship.key,
                conditions,
                replace_with,
            ).where(get_primary_key(model) == getattr(alias, self_key))

            lateral = subq.lateral(name=name)
            query = query.outerjoin(lateral, sa.true())
            alias = lateral
        else:
            query = _apply_conditions(
                query.outerjoin(
                    alias, get_primary_key(model) == getattr(alias, self_key)
                ),
                relationship.key,
                conditions,
                replace_with,
            )
    else:
        return query, _construct_strategy(orm.selectinload, relationship, load)

    load = _construct_strategy(orm.contains_eager, relationship, load, alias=alias)

    return query, load


@lru_cache(maxsize=128)
def _get_possible_quoted_names_for_replacement[T: orm.DeclarativeBase](
    model: type[T],
) -> Iterable[str]:
    name = get_table_name(model)

    return {
        f"{name}.",
        *[
            f"{d.dialect().identifier_preparer.quote(name)}."
            for d in [postgresql, mysql, sqlite, mssql, oracle]
        ],
    }


def _replace(string: str, replace_with: tuple[str, str]) -> str:
    return string.replace(*replace_with)


def _set_default_bind_param(
    orig_binds: dict[str, elements.BindParameter[Any]],
) -> Callable[[elements.BindParameter[Any]], None]:
    def _inner(bp: elements.BindParameter[Any]) -> None:
        orig_binds.setdefault(bp.key, bp)

    return _inner


def _get_bindparams(
    clause: elements.ColumnElement[Any], compiled: sa.Compiled
) -> list[elements.BindParameter[Any]]:
    """
    Build BindParameter objects for a compiled clause, preserving types.

    Traverses the original SQL expression to collect its BindParameter nodes
    (to reuse their type information), then recreates parameters using values
    from the compiled statement. This is useful when turning a clause into
    text via `sa.text(...)` and we need to re-bind parameters with correct
    SQLAlchemy types.

    Args:
        clause: Original SQL expression tree that was compiled.
        compiled: Result of `clause.compile(...)`; its ``.params`` supply values.

    Returns:
        List of ``bindparam(...)`` objects with names/values from ``compiled.params``
        and types taken from the original bind parameters when available.
    """
    orig_binds: dict[str, elements.BindParameter[Any]] = {}
    visitors.traverse(clause, {}, {"bindparam": _set_default_bind_param(orig_binds)})

    return [
        bindparam(
            name, value=val, type_=bp.type if (bp := orig_binds.get(name)) else None
        )
        for name, val in (compiled.params or {}).items()
    ]


def _apply_conditions[T: orm.DeclarativeBase](
    query: sa.Select[tuple[T]],
    key: str,
    conditions: Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]],
    replace_with: Iterable[tuple[str, str]] | None = None,
) -> sa.Select[tuple[T]]:
    """
    Apply a per-relationship condition transformer to `query`.

    The transformer receives a `Select[Related]`, may mutate ordering/where,
    and must return a `Select[Related]`. If `replace_with` is provided, the
    resulting WHERE clause is inlined as raw SQL via `sa.text(...)` after
    rewriting table-name prefixes (e.g., to point to a self-join alias).

    Notes:
        • We reset private `_where_criteria` before re-applying rewritten WHERE.
            This relies on SQLAlchemy internals; verify against SQLAlchemy upgrades.
        • `replace_with` is intended for self-joins where related tables are aliased.
            Provide pairs like `("user.", "user_parent.")`.

    Returns:
        A modified `Select` with conditions applied.
    """
    q = condition(query) if conditions and (condition := conditions.get(key)) else query
    if replace_with and (clause := q.whereclause) is not None:
        q._where_criteria = ()  # noqa: SLF001
        compiled = clause.compile(compile_kwargs={"render_postcompile": True})

        q = q.where(
            sa.text(reduce(_replace, replace_with, str(compiled))).bindparams(
                *_get_bindparams(clause, compiled)
            )
        )

    return q


def _apply_order_by[T: orm.DeclarativeBase](
    query: sa.Select[tuple[T]],
    relation_cls: type[T],
    order_by: tuple[str, ...] | None = None,
) -> sa.Select[tuple[T]]:
    ob = (
        (getattr(relation_cls, by).desc() for by in order_by)
        if order_by
        else (pk.desc() for pk in relation_cls.__table__.primary_key)
    )
    return query.order_by(*ob)


def _load_relationship[T: orm.DeclarativeBase](
    query: sa.Select[tuple[T]],
    params: _LoadRelationParams[T],
) -> tuple[sa.Select[tuple[T]], _AbstractLoad]:
    """Load a single relationship with appropriate strategy.

    Determines the best loading strategy for a relationship based on its
    characteristics (one-to-many, many-to-one, self-referential, etc.) and
    applies the necessary joins and load options.

    Args:
        query: SQLAlchemy select query to modify.
        params: Parameters for loading the relationship.

    Returns:
        Tuple of modified query and the load strategy.
    """
    (
        load,
        relationship,
        order_by,
        relation_cls,
        limit,
        model,
        conditions,
        is_alias,
        check_tables,
    ) = (
        params.load,
        params.relationship,
        params.order_by,
        params.relationship.mapper.class_,
        params.limit,
        params.model,
        params.conditions or {},
        params.is_alias,
        params.check_tables,
    )
    if relation_cls is model:
        return _load_self(
            query,
            _LoadSelfParams.from_relation_params(params),
            side="many" if relationship.uselist else "one",
        )

    if relationship.uselist:
        if limit is None:
            load = _construct_strategy(orm.subqueryload, relationship, load)
        else:
            subq = _apply_conditions(
                _apply_order_by(
                    sa.select(relation_cls).limit(limit), relation_cls, order_by
                ),
                relationship.key,
                conditions,
            )

            if (
                relationship.secondary is not None
                and relationship.secondaryjoin is not None
            ):
                compiled = str(
                    relationship.secondaryjoin.compile(
                        compile_kwargs={"literal_binds": True}
                    )
                )
                subq = subq.where(sa.text(compiled))
                if check_tables:
                    if relationship.secondary.description not in get_table_names(query):
                        query = query.outerjoin(
                            relationship.secondary, relationship.primaryjoin
                        )
                else:
                    query = query.outerjoin(
                        relationship.secondary, relationship.primaryjoin
                    )
            else:
                compiled = str(
                    relationship.primaryjoin.compile(
                        compile_kwargs={"literal_binds": True}
                    )
                )
                subq = subq.where(sa.text(compiled))

            lateral_name = (
                f"{get_table_name(relation_cls)}_{relationship.key}"
                if is_alias
                else get_table_name(relation_cls)
            )
            if check_tables and lateral_name in get_table_names(query):
                lateral_name = f"{lateral_name}_alias"

            lateral = subq.lateral(name=lateral_name)

            query = query.outerjoin(lateral, sa.true())
            load = _construct_strategy(
                orm.contains_eager, relationship, load, alias=lateral
            )
    elif is_alias:
        load = _construct_strategy(orm.selectinload, relationship, load)
    else:
        query = _apply_conditions(
            query.outerjoin(relation_cls, relationship.primaryjoin),
            relationship.key,
            conditions,
        )
        load = _construct_strategy(orm.contains_eager, relationship, load)

    return query, load


def _construct_loads[T: orm.DeclarativeBase](
    query: sa.Select[tuple[T]],
    excludes: set[type[T] | str],
    relationships: Sequence[orm.RelationshipProperty[T]],
    params: _ConstructLoadsParams[T],
) -> tuple[sa.Select[tuple[T]], list[_AbstractLoad | LoaderCriteriaOption] | None]:
    """Construct loading strategies for a sequence of relationships.

    Processes a sequence of relationships and builds the appropriate loading
    strategies (eager loading, selectin loading, etc.) while avoiding duplicates.

    Args:
        query: Base SQLAlchemy select query.
        excludes: Set of already processed models and relationship keys.
        relationships: Sequence of relationships to process.
        params: Parameters for constructing loads.

    Returns:
        Tuple of modified query and list of load options, or None if no options.
    """
    if not relationships:
        return query, None

    load: _AbstractLoad | None = None
    load_criteria = []
    for relationship in relationships:
        relation_cls = relationship.mapper.class_
        key = relationship.key
        if (
            params.conditions
            and (condition := params.conditions.get(key))
            and (
                (relationship.uselist and params.limit is None)
                or (relation_cls in excludes and key not in excludes)
                or (not relationship.uselist and params.model is relation_cls)
            )
        ) and (clause := condition(sa.select(relation_cls)).whereclause) is not None:
            load_criteria.append(orm.with_loader_criteria(relation_cls, clause))

        if relation_cls in excludes:
            if key not in excludes:
                query, load = _load_relationship(
                    query,
                    _LoadRelationParams.from_construct_loads_params(
                        params, relationship, load, is_alias=True
                    ),
                )
            continue

        excludes.update({relation_cls, key})
        query, load = _load_relationship(
            query,
            _LoadRelationParams.from_construct_loads_params(
                params, relationship, load, is_alias=False
            ),
        )

    return query, [load, *load_criteria] if load else None


@lru_cache(maxsize=1028)
def _select_with_relationships[T: orm.DeclarativeBase](
    params: _LoadParams[T],
) -> sa.Select[tuple[T]]:
    """Build a select query with relationship loading based on load parameters.

    This is the core function that processes load parameters and constructs
    the appropriate SQLAlchemy query with joins and loading strategies.

    Args:
        params: Load parameters containing model, relationships, and options.

    Returns:
        Configured SQLAlchemy Select statement.
    """
    loads, model, query, node = (
        list(params.loads),
        params.model,
        params.query,
        params.node,
    )
    if orm.DeclarativeBase in model.__bases__ or model is orm.DeclarativeBase:
        raise TypeError("model must not be orm.DeclarativeBase")

    if query is None:
        query = sa.select(model)

    options = []
    excludes: set[type[T] | str] = set()
    while loads:
        result = _bfs_search(model, loads.pop(), node)
        if not result:
            continue
        query, load = _construct_loads(
            query, excludes, result, _ConstructLoadsParams.from_params(params)
        )
        if load:
            options += load

    if options:
        query = query.options(*options)

    return query.distinct() if params.distinct else query


@lru_cache(maxsize=128)
def _find_self_key[T: orm.DeclarativeBase](
    model: type[T],
) -> str:
    """Find the foreign key column for self-referential relationships.

    Looks for a foreign key in the model that references the model's own
    primary key, which indicates a self-referential relationship.

    Args:
        model: SQLAlchemy model class to examine.

    Returns:
        Name of the self-referential foreign key column, or empty string if none found.
    """
    return next(
        (
            fk.parent.name
            for fk in model.__table__.foreign_keys
            if get_primary_key(model).name == fk.column.name
            and fk.column.table.name == fk.parent.table.name
        ),
        "",
    )


def select_with_relationships[T: orm.DeclarativeBase](
    *loads: str,
    **params: Unpack[_LoadParamsType[T]],
) -> sa.Select[tuple[T]]:
    """Create a SQLAlchemy select statement with automatic relationship loading.

    This is the main function for building select queries with eager loading of relationships.
    It automatically constructs the necessary joins and load strategies based on the specified
    relationship paths.

    Args:
        model: type[T]
            The SQLAlchemy model class to select from.
        loads: tuple[str, ...]
            Tuple of relationship.key paths to load.
            Defaults to () (no relationships).
        node: Node
            Node instance containing relationship mappings.
            Defaults to None (uses singleton).
        check_tables: bool
            Whether to check for existing tables in query to avoid duplicate joins.
            Defaults to False.
        conditions: Mapping[str, Callable[[sa.Select[tuple[T]]], sa.Select[tuple[T]]]] | None
            Mapping of relationship keys to condition functions for filtering.
            Defaults to None.
        self_key: str
            Foreign key column name for self-referential relationships.
            Defaults to None (auto-detected).
        order_by: tuple[str, ...]
            Tuple of column names for ordering relationship results.
            Defaults to None (uses primary key).
        query: sa.Select[tuple[T]]
            Existing select query to extend.
            Defaults to None (creates new query).
        distinct: bool
            Whether to apply DISTINCT to the query. For edge cases, use .unique() instead.
            Defaults to False.
        limit: int | None
            Maximum number of related records to load per relationship. Defaults to 50.

    Returns:
        A SQLAlchemy Select statement with configured eager loading.

    Example:
        >>> query = select_with_relationships(
        ...     "roles", "profile",
        ...     model=User,
        ...     conditions={
        ...         "roles": add_conditions(Role.active == True),
        ...         "profile": lambda q: q.order_by(None).order_by(
        ...             Profile.name.asc()
        ...         ),
        ...     },
        ...     limit=10,
        ... )
    """

    params["conditions"] = frozendict(params.get("conditions", {}))
    if "self_key" not in params:
        params["self_key"] = _find_self_key(params["model"])

    return _select_with_relationships(_LoadParams[T](**params, loads=loads))
