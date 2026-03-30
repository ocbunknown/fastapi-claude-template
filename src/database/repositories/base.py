from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.base import Base
from src.database.repositories.crud import CRUDRepository


class BaseRepository[M: Base]:
    __slots__ = ("_session", "_crud", "model")

    def __init__(self, session: AsyncSession, model: type[M]) -> None:
        self._session = session
        self.model = model
        self._crud = CRUDRepository(session, model)
