from datetime import datetime

from pydantic import BaseModel, Field
from uuid_utils.compat import UUID, uuid4


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_timestamp: float = Field(default_factory=datetime.now().timestamp)
