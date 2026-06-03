from WebpageSaver.Crawler.Assets.Asset import Asset
from pydantic import BaseModel, Field
from typing import Any
from yarl import URL
import logging

class GotRequest(BaseModel):
    url: str = Field(default = None)
    content_type: str = Field(default = None)
    asset: Asset = Field(default = None)
    request: Any = Field(default = None, exclude = True)
    response: Any = Field(default = None, exclude = True)

    started_at: float = Field(default = None)
    ended_at: float = Field(default = None)
    interrupted_at: float = Field(default = None)

    done: bool = Field(default = False)

    def getContentType(self) -> str:
        if self.content_type:
            return self.content_type

        return ''

    def url_matches(self, url: str):
        return URL(url) == URL(self.url)
