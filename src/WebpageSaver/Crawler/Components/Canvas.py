from pydantic import BaseModel, Field
from typing import Optional

class Canvas(BaseModel):
    id: str = Field()
    width: Optional[int] = Field(default = None)
    height: Optional[int] = Field(default = None)
    className: Optional[str] = Field(default = None)
    id_attribute: Optional[str] = Field(default = None)
