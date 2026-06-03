from pydantic import Field, BaseModel, ConfigDict
from typing import Any
from WebpageSaver import app
import urllib
import logging
import aiohttp
import aiofiles

class Asset(BaseModel):
    '''
    Anything that contains url or media data
    '''
    url: str = Field(default = None)
    bs_node: Any = Field(default = None, exclude = True)
    model_config = ConfigDict(extra='allow')

    def getName(self):
        d = self.url.split('/')

        return d[-1]

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

    def get_url(self):
        return self.url

    def has_url(self):
        return self.url != None

    async def download(self, dir: str):
        await self.download_function(dir)

    async def download_function(self, dir, name: str = None):
        if name == None:
            name = self.getEncodedURL()

        if self.url == None:
            logging.info('no url...')
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                async with aiofiles.open(str(dir.joinpath(name)), mode='wb') as f:
                    async for chunk in response.content.iter_chunked(4096):
                        await f.write(chunk)

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
