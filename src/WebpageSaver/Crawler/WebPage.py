from pydantic import BaseModel, Field
from typing import Generator
from datetime import datetime
from pathlib import Path
from WebpageSaver.Crawler.Assets.Asset import Asset
from WebpageSaver.Crawler.Assets.Meta import Meta
from WebpageSaver.Crawler.Assets.Favicon import Favicon
from WebpageSaver.Crawler.Components.GotRequest import GotRequest
from WebpageSaver.Crawler.Components.Canvas import Canvas
from WebpageSaver.Crawler.Components.Utils import toURLWithoutMeaninglessDiffs
from WebpageSaver import config
from yarl import URL
from functools import cache
import logging
import brotli
import json
import shutil

class WebPage(BaseModel):

    # Page data

    title: str = Field(default = 'Untitled')
    taken: float = Field(default = None)

    # HTTP

    status: int = Field(default = 200)
    redirected_to: str = Field(default = None) # identify

    # App properties

    from_html: bool = Field(default = False) # or better "created_from_html"
    has_screenshot: bool = Field(default = True)

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

    # iFrames

    is_iframe: bool = Field(default = False)
    common_page_id: str = Field(default = None)
    linked_iframe_pages: list[str] = Field(default = [])

    # Encoding

    encodings: list[str] = Field(default = ['utf-8'])
    common_encoding_id: int = Field(default = 0)

    # Assets

    assets_links: dict[int, GotRequest] = Field(default = {})
    canvases: dict[str, Canvas] = Field(default = {})

    # Hyperlinks

    linked_pages: list[str] = Field(default = [])

    # Internal

    identify: str = Field(default = None)
    root_directory: str = Field(default = None, exclude = True)
    path_to: str = Field(default = None)
    root_file: str = Field(default = 'index.html')
    data_file: str = Field(default = 'data.json')
    assets_directory: str = Field(default = 'assets')
    thumbs_directory: str = Field(default = 'thumbs')

    _cached_links = None
    _cached_iframes = None

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
        try:
            return self.encodings[self.common_encoding_id]
        except Exception as e:
            logging.exception(e)
            return 'utf-8'

    def setDate(self) -> str:
        '''
        Creates ID.
        '''
        _now = datetime.now()
        self.identify = f"{_now.strftime('%Y%m%d%H%M%S%f')}"
        self.path_to = self.identify
        self.taken = _now.timestamp()

        return self.identify

    def getScreenshotURL(self, filename: str = 'viewport.jpeg'):
        ids = self.identify
        if self.redirected_to:
            ids = self.redirected_to
 
        return '/page/screenshot?id={0}&file={1}'.format(ids, filename)

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
        if self.common_page_id != None:
            return self.root_directory.joinpath(self.common_page_id).joinpath(self.assets_directory)

        return self.getDir().joinpath(self.assets_directory)

    def getThumbsDir(self) -> Path:
        return self.getDir().joinpath(self.thumbs_directory)

    def getIndexPageText(self, encoding: str = 'utf-8'):
        if encoding != 'br':
            text = self.getRootFile().read_text(encoding = encoding)
        else:
            text = brotli.decompress(self.getRootFile().read_bytes()).decode('utf-8')

        return text

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

        with open(self.getRootFile(), 'wb') as file:
            file.write(html)

        #try:
        #    with open(self.getRootFile(), 'w', encoding = self.encoding) as file:
        #        file.write(html)
        #except Exception as e:
        #    logging.error("Error when writing file, encoding is {0}, trying writing bytes. ".format(self.encoding))
        #    logging.exception(e)

    def saveData(self):
        d = self.model_dump(exclude_none = True, exclude_defaults = True)
        with open(str(self.getDataFile()), 'w', encoding = 'utf-8') as file:
            json.dump(d, file, ensure_ascii = False)

        c = self._selfCachedVersion()
        if c:
            c.setData(d)
            c.save()

    def setURL(self, url: str):
        u = URL(url).origin().human_repr()
        if u[-1] != '/':
            u += '/'

        self.relative_url = u
        self.base_url = u

    def getReadableTaken(self, with_day: bool = True):
        if self.taken == None:
            return None

        formats = '%Y/%m/%d, %H:%M:%S'
        if with_day == False:
            formats = '%H:%M:%S'

        return datetime.fromtimestamp(self.taken).strftime(formats)

    def getAssets(self) -> Generator[GotRequest]:
        for i, v in self.assets_links.items():
            yield v

    def getAssetByUrl(self, url: str, content_type: str = None):
        '''
        Unwraps asset by its URL
        '''

        for itm in self.assets_links.items():
            if itm[1].compare_urls(url, self):
                return (itm[0], itm[1])

        # 2nd time
        # helpful for relative URLS from CSS files
        for itm in self.assets_links.items():
            if itm[1].compare_urls(url, self, second_time = True, content_type = content_type):
                return (itm[0], itm[1])

    def getAssetPathById(self, index: int):
        return self.getAssetsDir().joinpath(str(index))

    def getAssetById(self, id: int):
        return self.assets_links.get(int(id))

    def addAsset(self, ident: int, request: GotRequest):
        self.assets_links[ident] = request

    def getRelativeURL(self, url: str, ignore_host_errors: bool = False, ruofc: bool = True):
        relative_url = str(self.relative_url)
        if url == None:
            return relative_url

        u1 = URL(url)
        i = URL(self.url)

        if not url.startswith('http') and url.startswith('data:') == True:
            return url

        # Relative urls. WORKAROUND
        if url.startswith('..'):
            return URL(self.url).joinpath(url).human_repr()

        if relative_url[-1] == '/':
            relative_url = relative_url[:-1]

        # Relative link
        if url.startswith(relative_url) == False and url.startswith('http') == False and url[0] != '/':
            if ruofc == True:
                if i.suffix != None and i.suffix != '':
                    return Asset.getDecodedURL(URL(self.url.replace('/' + i.name, '')).joinpath(url).human_repr())

                return Asset.getDecodedURL(URL(self.url).joinpath(url).human_repr())
            else:
                if url[0] == '/':
                    return relative_url + url
                else:
                    return relative_url + '/' + url

        if u1.host == None:
            if url == None or len(url) == 0:
                return relative_url

            if url[0] == '/':
                return relative_url + url
            else:
                return relative_url + '/' + url

        # Not belongs to domain of this page
        if URL(relative_url).host != u1.host and ignore_host_errors == False:
            return url

        if len(url) > 0:
            if u1.host in relative_url:
                return url

            if url[0] == '/':
                return relative_url + url
            else:
                return relative_url + '/' + url
        else:
            return relative_url

        #return URL(self.relative_url).(url).human_repr()

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

    def linkPage(self, page):
        self._cached_links = None
        self.linked_pages.append(page.identify)

    def findLinkedPageByUrl(self, url: str):
        found = None
        u = self.getRelativeURL(url)

        for page in self.getLinkedPages():
            if URL(page.url) == URL(u):
                found = page

                break

        return found

    def getLinkedPages(self, every_pages: bool = False) -> Generator:
        from WebpageSaver.Cache import Page as DBPage

        if every_pages:
            p = DBPage.select().where(DBPage.url == toURLWithoutMeaninglessDiffs(self.url)).order_by(DBPage.taken_at.desc())
            linked = list()
            for i in p:
                for f in i.toModel().linked_pages:
                    linked.append(f)

            for g in DBPage.select().where(DBPage.path_to.in_(linked)).order_by(DBPage.taken_at.desc()):
                yield g.toModel()

            return

        if self._cached_links == None:
            self._cached_links = DBPage.select().where(DBPage.path_to.in_(self.linked_pages)).order_by(DBPage.taken_at.desc())

        for itm in self._cached_links:
            yield itm.toModel()

    def getIframes(self) -> Generator:
        from WebpageSaver.Cache import Page as DBPage

        if self._cached_iframes == None:
            self._cached_iframes = DBPage.select().where(DBPage.path_to.in_(self.linked_iframe_pages))

        for itm in self._cached_iframes:
            yield itm.toModel()

    def _selfCachedVersion(self):
        from WebpageSaver.Cache import Page as DBPage

        return DBPage.select().where(DBPage.path_to == self.identify).first()

    def delete_self(self):
        '''
        Deletes page dir
        '''
        shutil.rmtree(str(self.getDir()))

    def getShortTitle(self, count: int = 15):
        title = self.title
        if self.title == None or len(self.title) == 0:
            title = self.url

        d = title[0:count]

        if d == title:
            return title

        return d + '...'

    def getFavicon(self):
        try:
            first_url = self.favicons[0].url
            asset = self.getAssetByUrl(first_url)
            if asset != None:
                return '/page/asset?id={0}&path={1}'.format(self.identify, asset[0])
                
            return first_url
        except Exception as e:
            logging.exception(e)
            return '/static/no_asset.jpg'

    def getRedirection(self):
        from WebpageSaver.Cache import Page as DBPage

        d = DBPage.select().where(DBPage.path_to == self.redirected_to).first()
        if d:
            return d.toModel()

    def getMediaFromRequests(self, set_local_urls: bool = True, selector: str = '[src]'):
        check_exts = []
        check_ct = ''

        match(selector):
            case 'img[src]':
                check_exts = ['jpg', 'png']
                check_ct = 'image/'
            case 'video[src]':
                check_exts = ['mp4', 'mov']
                check_ct = 'video/'

        for r, e in self.assets_links.items():
            u = URL(e.url)
            content_type = e.content_type
            url = '/page/asset?id={0}&path={1}'.format(self.identify, r)
            if set_local_urls == False:
                url = e.url

            asset = e.asset
            asset.local_url = url

            if content_type != None and content_type.startswith(check_ct):
                yield asset
            elif u.suffix != None and u.suffix in check_exts:
                yield asset
