from pydantic import BaseModel, Field
from typing import Optional

class Canvas(BaseModel):
    id: str = Field()
    width: Optional[int] = Field(default = None)
    height: Optional[int] = Field(default = None)
    className: Optional[str] = Field(default = None)
    id_attribute: Optional[str] = Field(default = None)

    def toHTML(self, page):
        return "<img style=\"width:{1}px;height:{2}px;\" src=\"{0}\">".format('/page/screenshot?id=' + page.identify + '&file=' + self.id + '.png', self.width, self.height)
