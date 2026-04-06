from pydantic import BaseModel, ConfigDict


class Contract(BaseModel):
    model_config = ConfigDict(from_attributes=True)
