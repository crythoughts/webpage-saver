from pydantic import Field, BaseModel, ConfigDict
from typing import Any
from WebpageSaver import app
from yarl import URL
import urllib
import logging
import aiohttp
import aiofiles

class Asset(BaseModel):
    '''
    Anything that contains url or media data
    '''
    url: str = Field(default = None)
    local_url: str = Field(default = None, exclude = True)
    bs_node: Any = Field(default = None, exclude = True)
    model_config = ConfigDict(extra='allow')

    def getName(self):
        d = self.url.split('/')

        return d[-1]

    def getShortURL(self):
        d = self.url[0:50]

        if d == self.url:
            return self.url

        return d + '...'

    # we know that contents are downloaded so it will available in the displayment
    def moveUrlToAnotherAttr(self, page):
        _node = self.get_node()

        if _node != None and (_node.get('href') or _node.get('src')):
            _node[page.getOrigAttr()] = self.url
            _key = 'href'

            if _node.get('src') != None and _node.get('src') != '':
                _key = 'src'

            _node[page.getKeyAttr()] = _key
            _node[_key] = ''

    def decompose(self):
        self.bs_node.decompose()

    def set_url(self, href: str):
        if not href.startswith('http'):
            if href.startswith('data:') == True:
                return

        self.url = href

    def set_local_url(self, href: str):
        self.local_url = href

    def get_url(self):
        return self.url

    def has_url(self):
        return self.url != None

    async def download(self, dir: str):
        await self.download_function(dir)

    async def download_function(self, dir, name: str = None):
        from WebpageSaver.Crawler.Components.GotRequest import GotRequest

        if name == None:
            name = self.getEncodedURL()

        if self.url == None:
            logging.info('no url...')
            return

        req = GotRequest(
            url = self.url,
            content_type = '',
            asset = Asset(
                url = self.url
            )
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                async with aiofiles.open(str(dir.joinpath(name)), mode='wb') as f:
                    async for chunk in response.content.iter_chunked(4096):
                        await f.write(chunk)

        return req

    def getEncodedURL(self):
        return urllib.parse.quote(self.url)

    @staticmethod
    def getDecodedURL(url):
        return urllib.parse.unquote(url)

    @staticmethod
    def encodeURL(url):
        return urllib.parse.quote(url)

    def set_node(self, bs_node):
        self.bs_node = bs_node

    def get_node(self):
        return self.bs_node

    def _get_url_by_id(self, from_page, id: int = None):
        return '/page/asset?id={0}&path={1}'.format(from_page.identify, id)

    def getLocalURL(self, from_page, id: int = None, path: str = None):
        #if id != None:
        #    return self._get_url_by_id(from_page, id)

        p = URL(path)

        # TODO REMOVE
        # If asset is not from site's host
        if p.host and URL(from_page.url).host != p.host:
            return self._get_url_by_id(from_page, id)
        else:
            u = URL('/page/asset/{0}{1}'.format(from_page.identify, p.path_qs))

            return u.human_repr()

    def hasLocalURL(self):
        return self.local_url not in [None, '']
