from pydantic import BaseModel, Field
from typing import Generator
from datetime import datetime
from pathlib import Path
from WebpageSaver.Crawler.Assets.Asset import Asset
from WebpageSaver.Crawler.Assets.Meta import Meta
from WebpageSaver.Crawler.Assets.Script import Script
from WebpageSaver.Crawler.Assets.Link import Link
from WebpageSaver.Crawler.Assets.URL import URL
from WebpageSaver.Crawler.Assets.Media import Media
from WebpageSaver.Crawler.Assets.Favicon import Favicon
from WebpageSaver.Crawler.Components.GotRequest import GotRequest
from WebpageSaver import config
import logging
import json
import shutil

class WebPage(BaseModel):

    # Page data

    title: str = Field(default = None)
    taken: float = Field(default = None)

    # URLs

    url: str = Field()
    base_url: str = Field(default = None)
    relative_url: str = Field(default = None)

    # Page content

    meta: list[Meta] = Field(default = [])
    favicons: list[Favicon] = Field(default = [])
    #script: list[Script] = Field(default = [])
    #links: list[Link] = Field(default = [])
    #hyperlinks: list[URL] = Field(default = [])
    #media: list[Media] = Field(default = [])

    # Other

    identify: str = Field(default = None)
    root_directory: str = Field(default = None, exclude = True)
    path_to: str = Field(default = None)
    root_file: str = Field(default = 'index.html')
    data_file: str = Field(default = 'data.json')
    assets_directory: str = Field(default = 'assets')
    thumbs_directory: str = Field(default = 'thumbs')

    encodings: list[str] = Field(default = [])
    common_encoding_id: int = Field(default = 0)

    assets_links: dict[int, GotRequest] = Field(default = {})
    linked_pages: list[str] = Field(default = [])

    def init(self, path: Path):
        self.root_directory = path

        self.setDate()
        self.getDir().mkdir(exist_ok=True)
        self.getThumbsDir().mkdir(exist_ok=True)
        self.getAssetsDir().mkdir(exist_ok=True)
        #self._create_index(path)

    def addEncoding(self, encoding: str):
        '''
        Just adds the encoding
        '''
        if encoding not in self.encodings and encoding is not None:
            self.encodings.append(encoding)

    def setEncoding(self, val: str):
        '''
        Sets the encoding as default
        '''

        self.addEncoding(val)
        if val != None:
            self.common_encoding_id = self.encodings.index(val)
            logging.info('setting encoding to ' + str(val))

    @property
    def encoding(self) -> str:
        #print(self.encodings, self.common_encoding_id)
        return self.encodings[self.common_encoding_id]

    def setDate(self) -> str:
        '''
        Creates ID.
        '''
        _now = datetime.now()
        self.identify = f"{_now.strftime('%Y%m%d%H%M%S%f')}"
        self.path_to = self.identify
        self.taken = _now.timestamp()

        return self.identify

    def getDir(self) -> Path:
        '''
        Returns directory of the page in storage.
        '''
        return self.root_directory.joinpath(self.identify)

    def getRootFile(self) -> Path:
        '''
        Returns "index.html" path.
        '''
        return self.getDir().joinpath(self.root_file)

    def getDataFile(self) -> Path:
        return self.getDir().joinpath(self.data_file)

    def getAssetsDir(self) -> Path:
        return self.getDir().joinpath(self.assets_directory)

    def getThumbsDir(self) -> Path:
        return self.getDir().joinpath(self.thumbs_directory)

    def _create_index(self):
        '''
        Creates dir in storage, index.html and assets.
        '''

        index_file = open(str(self.getRootFile()), 'w', encoding = 'utf-8')
        index_file.close()

    def write(self, html: str):
        '''
        Writes changes to index.html
        '''
        #_detect = chardet.detect(html.encode('utf-8', errors='ignore'))
        #self.setEncoding(_detect.get('encoding'))

        try:
            with open(self.getRootFile(), 'w', encoding = self.encoding) as file:
                file.write(html)
        except Exception as e:
            logging.error("Error when writing file, encoding is {0}, trying writing bytes. ".format(self.encoding))
            logging.exception(e)

            with open(self.getRootFile(), 'wb') as file:
                file.write(html)

    def saveData(self):
        d = self.model_dump(exclude_none = True, exclude_defaults = True)
        with open(str(self.getDataFile()), 'w', encoding = 'utf-8') as file:
            json.dump(d, file, ensure_ascii = False)

        c = self._selfCachedVersion()
        if c:
            c.setData(d)
            c.save()

    def getReadableTaken(self):
        if self.taken == None:
            return None

        return datetime.fromtimestamp(self.taken).strftime("%d/%m/%Y, %H:%M:%S")

    def getAssets(self) -> Generator[GotRequest]:
        for i, v in self.assets_links.items():
            yield v

    def getAssetByUrl(self, url: str):
        '''
        Unwraps asset by its URL
        '''
        _a = self.assets_links.items()
        for itm in _a:
            if itm[1].url == url:
                return (itm[0], itm[1])

    def getAssetPathById(self, index: int):
        return self.getAssetsDir().joinpath(str(index))

    def getAssetById(self, id: int):
        return self.assets_links.get(int(id))

    def addAsset(self, ident: int, request: GotRequest):
        self.assets_links[ident] = request

    def getRelativeURL(self, url: str):
        if not url.startswith('http'):
            if url.startswith('data:') == True:
                return url

        if url.startswith(self.relative_url) or url.startswith('http'):
            return url

        if self.relative_url[-1] == '/':
            self.relative_url[-1] = ''

        if len(url) > 0:
            if url[0] == '/':
                return self.relative_url + url
            else:
                return self.relative_url + '/' + url
        else:
            return self.relative_url # ???

    @classmethod
    def fromPath(cls, path_to: str):
        c = config.webpages_dir.joinpath(path_to).joinpath('data.json')
        d = json.loads(c.read_text(encoding = 'utf-8'))
        m = WebPage.model_validate(d)
        m.root_directory = config.webpages_dir.joinpath(path_to).parent
        m.path_to = path_to

        return m

    def dump(self):
        return self.model_dump(exclude_none = True, exclude_defaults = True)

    def getKeyAttr(self):
        return 'data-__orig-key'

    def getOrigAttr(self):
        return 'data-__orig'

    def has_linked_pages(self):
        return len(self.linked_pages) > 0

    def getLinkedPages(self) -> Generator:
        from WebpageSaver.Cache import Page as DBPage

        for itm in DBPage.select().where(DBPage.path_to.in_(self.linked_pages)).order_by(DBPage.taken_at.desc()):
            yield itm.toModel()

    def _selfCachedVersion(self):
        from WebpageSaver.Cache import Page as DBPage

        return DBPage.select().where(DBPage.path_to == self.identify).first()

    def delete_self(self):
        '''
        Deletes page dir
        '''
        shutil.rmtree(str(self.getDir()))
