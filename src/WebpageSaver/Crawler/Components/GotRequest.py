from WebpageSaver.Crawler.Assets.Asset import Asset
from pydantic import BaseModel, Field
from typing import Any
from yarl import URL
import logging

class GotRequest(BaseModel):
    url: str = Field(default = None)
    content_type: str = Field(default = None)
    status: int = Field(default = 200)

    asset: Asset = Field(default = None)
    request: Any = Field(default = None, exclude = True)
    response: Any = Field(default = None, exclude = True)
    is_first_ever: bool = Field(default = False)

    started_at: float = Field(default = None)
    ended_at: float = Field(default = None)
    interrupted_at: float = Field(default = None)

    done: bool = Field(default = False)
    common_to_iframe: bool = Field(default = False)

    internal_id: int = Field(default = None, exclude = True)
    _frame: Any = None

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
            u11 = URL(url)
            u22 = URL(self.asset.url)

            if u11.host == u22.host:
                # comparing urls
                if url in self.asset.url or u11.path in u22.path:
                    #print(content_type, self.getContentType())

                    if content_type and content_type in self.getContentType():
                        return True # not True but TRUE!!!!!!

                    return True

                actual_parts = [p for p in u11.parts if p]
                matches = [part for part in u22.parts if part in actual_parts]
                match_count = len(matches)

                # comparing urls by match count
                if match_count > (len(u22.parts) / 2):
                    return True

        u1 = URL(page.getRelativeURL(self.asset.url, ruofc = False)).with_scheme('https')
        u2 = URL(page.getRelativeURL(url, ruofc = False)).with_scheme('https')

        if u1 == u2:
            return True

        if URL(self.asset.url).with_scheme('https') == URL(url):
            return True

        if self.url == Asset.getDecodedURL(url):
            return True

        return False

    def dump(self):
        return self.model_dump(exclude_none = True, exclude_defaults = True)
