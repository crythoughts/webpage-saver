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

    def getDownloadedIn(self) -> float:
        return round(self.ended_at - self.started_at, 2)

    def url_matches(self, url: str):
        return URL(url) == URL(self.url)

    def compare_urls(self, url: str, page, second_time: bool = False, content_type: str = None) -> bool:
        # it can be made better!

        # TODO remove when better solution will be found
        if second_time:
            if url in self.asset.url:
                #print(content_type, self.getContentType())

                if content_type in self.getContentType():
                    return True # not True but TRUE!!!!!!

                return True

        if URL(page.getRelativeURL(self.asset.url)) == URL(page.getRelativeURL(url)):
            return True

        if URL(self.asset.url) == URL(url):
            return True

        if self.url == Asset.getDecodedURL(url):
            return True

        return False
