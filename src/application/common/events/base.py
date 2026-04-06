from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
