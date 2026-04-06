from pydantic import BaseModel, ConfigDict


class Request(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)
