from pydantic import BaseModel, Field
from typing import Union

class BaseConcept(BaseModel):
    name: str
    description_common: str  # summary of the concept
    description_variation: str  # how the concept varies across instances
    group_id: int = None
    depth: int = None
    instances: list[str] = Field(default_factory=list)  # list of node uuids
    popularity: Union[float, None] = None

    def __init__(self, **data):
        super().__init__(**data)