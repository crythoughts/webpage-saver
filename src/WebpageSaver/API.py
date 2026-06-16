from WebpageSaver.Crawler.Webdrivers.WebdriversRepo import WebdriversRepo
from WebpageSaver.Crawler.Webdrivers.Webdriver import Webdriver
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Crawler import Crawler
from WebpageSaver import config
from WebpageSaver.Cache import Cache, Page
from WebpageSaver.Crawler.Components.Utils import toURLWithoutMeaninglessDiffs
from yarl import URL
from peewee import fn
import logging
import aiohttp
import xml.etree.ElementTree as ET
import asyncio

cache = Cache()

class API:
    '''
    API Service
    '''

    def __init__(self):
        self.w_repo = WebdriversRepo()

    def getWebdrivers(self, conv: bool = True) -> list:
        payload = list()
        for wd in self.w_repo.getAll():
            if conv:
                payload.append(wd.model_dump(exclude_none = True))
            else:
                payload.append(wd)

        return payload

    async def getAvailableWebdrivers(self) -> dict:
        return await self.w_repo.get_versions()

    async def webdriverFromChannel(self, channel: dict):
        d = channel.get('downloads').get('chrome-headless-shell')
        platform = self.w_repo.getPlatform()
        s = None

        for i in d:
            if i.get('platform') == platform:
                s = i

        assert s != None

        shell_url = s.get('url')

        w = Webdriver(
            shell_path = '',
            orig_url = shell_url,
            channel = channel.get('channel'),
            version = channel.get('version'),
            platform = platform
        )
        await w.downloadFromOrigURL()
        self.w_repo.add(w)

        return w

    async def savePage(self, 
                       url: str, 
                       webdriver_id: int = None,
                       link_pages: list[WebPage] = None,
                       remove_js: bool = False,
                       scroll_down: bool = True,
                       scroll_times: int = 5,
                       sleep_before_crawl_s: float = 1,
                       page_load_timeout_s: float = 10,
                       ignore_assets_no_length: bool = False,
                       max_asset_size_mb: float = 10,
                       conv: bool = True):
        crawler = Crawler()

        try:
            if sleep_before_crawl_s != None:
                crawler.sleep_before_crawl_s = sleep_before_crawl_s
            if page_load_timeout_s != None:
                crawler.page_load_timeout_s = page_load_timeout_s
        except Exception as e:
            logging.exception(e)

        if ignore_assets_no_length != None:
            crawler.ignore_assets_no_length = ignore_assets_no_length
        if max_asset_size_mb != None:
            crawler.max_asset_size_bytes = round(max_asset_size_mb * 1000 * 1000)

        payload = list()
        webdriver = self.w_repo.getById(webdriver_id)
        await webdriver.start()

        page = WebPage(
            url = url
        )
        page.init(config.webpages_dir)

        fnl_page = await crawler.sendPage(page, webdriver, link_pages, 
                                          scroll_down = scroll_down,
                                          scroll_times = scroll_times)

        if conv:
            payload.append(fnl_page.model_dump(exclude_none = True))
        else:
            payload.append(fnl_page)

        return payload

    # TODO rework
    async def savePageByHTML(self, url: str,
                            html: str, 
                            link_pages: list[WebPage] = None, 
                            webdriver_id: int = None,
                            title: str = None, 
                            remove_js: bool = True):
        crawler = Crawler()
        payload = list()
        webdriver = self.w_repo.getById(webdriver_id)
        await webdriver.start()

        page = WebPage(
            url = url,
            from_html = True
        )
        page.init(config.webpages_dir)

        fnl_page = await crawler.sendPage(page, webdriver, link_pages, html = html, remove_js = remove_js, from_html = True)

        if title != None:
            fnl_page.title = title

        payload.append(fnl_page.model_dump(exclude_none = True))

        return payload

    def getPages(self):
        payload = list()
        for page in cache.getPages():
            payload.append(page.toModel().dump())

        return payload

    def getPagesById(self, ids: list[str], convert: bool = True) -> list[WebPage]:
        payload = list()
        for item in Page.select().where(Page.path_to.in_(ids)):
            if convert == True:
                payload.append(item.toModel().dump())
            else:
                payload.append(item.toModel())

        return payload

    def getPagesByURL(self, url: str, approximate_max_time: float, conv: bool = True) -> list[WebPage]:
        payload = list()
        items = Page.select().where(Page.url == toURLWithoutMeaninglessDiffs(url)).order_by(fn.ABS(Page.taken_at - approximate_max_time))

        for item in items:
            if conv:
                payload.append(item.toModel().dump())
            else:
                payload.append(item.toModel())

        return payload

    def deletePagesById(self, ids: list[str]) -> None:
        for item in Page.select().where(Page.path_to.in_(ids)):
            i = item.toModel()
            i.delete_self()
            item.delete_instance()

    def editPageById(self, ids: list[str], new_taken: float = None) -> None:
        for item in Page.select().where(Page.path_to.in_(ids)):
            if new_taken != None:
                i = item.toModel()
                i.taken = new_taken

            i.saveData()

    def findPagesByURL(self, url: str, 
                       conv: bool = True,
                       conv_models: bool = True,
                       find_by_start: bool = False,
                       exact_match: bool = False
                       ):

        find_url = url

        if find_url.startswith('http') == False:
            find_url = 'https://' + url
 
        u = URL(find_url)
        mode = None
        payload = list()

        # If URL is empty or not recognized as URL: Keywords search
        if mode == None and (url == '' or u.host == None):
            pages = Page.select()
            if url != '':
                pages = pages.where(Page.title.startswith(find_url)).where(Page.is_frame == 0)
                mode = 'keywords_search'
            else:
                mode = 'empty_search'

            pages = pages.order_by(Page.taken_at.desc())

            for p in pages:
                if conv:
                    payload.append(p.toModel().dump())
                else:
                    if conv_models:
                        payload.append(p.toModel())
                    else:
                        payload.append(p)

        # Finding by start of the URL
        if mode == None and find_by_start:
            pages = Page.select().where(Page.url.startswith(find_url)).where(Page.is_frame == 0).group_by(Page.url).order_by(Page.taken_at.desc())
            mode = 'urls'

            for p in pages:
                if conv:
                    payload.append(p.toModel().dump())
                else:
                    if conv_models:
                        payload.append(p.toModel())
                    else:
                        payload.append(p)

        # Thinking that it is a domain
        if mode == None:
            if url.startswith('http') == False and (u.path == '/' or u.path == ''):
                mode = 'domain_search'
                pages = Page.select()
                find_url = u.host

                if exact_match:
                    pages = pages.where(Page.domain == u.host)
                else:                        
                    pages = pages.where(Page.domain.like(u.host))

                pages = pages.where(Page.is_frame == 0).order_by(Page.taken_at.desc())
                for p in pages:
                    if conv:
                        payload.append(p.toModel().dump())
                    else:
                        if conv_models:
                            payload.append(p.toModel())
                        else:
                            payload.append(p)
            else:
                mode = 'accurate_url'

                find_url = toURLWithoutMeaninglessDiffs(find_url)

                pages = Page.select()

                if exact_match:
                    pages = pages.where(Page.url == find_url)
                else:
                    pages = pages.where(Page.url % find_url)

                pages = pages.where(Page.is_frame == 0).order_by(Page.taken_at.desc())

                for p in pages:
                    if conv:
                        payload.append(p.toModel().dump())
                    else:
                        if conv_models:
                            payload.append(p.toModel())
                        else:
                            payload.append(p)

        return {
            'type': mode,
            'items': payload,
            'url': find_url
        }

    async def saveSitemap(self, url: str, 
                          conv: bool = True, 
                          max_semaphore: int = 3,
                          max_pages: int = None,
                          ignore_already_saved: bool = False
                          ):
        session_timeout = aiohttp.ClientTimeout(total=None,sock_connect=10,sock_read=10)
        data = None
        self.items = []

        async with aiohttp.ClientSession(timeout = session_timeout) as session:
            async with session.get(url) as response:
                data = await response.text()

        root = ET.fromstring(data)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [loc.text for loc in root.findall('.//ns:url/ns:loc', namespaces)]
        self.d_c = 0

        if ignore_already_saved == True:
            p_a = list()

            for url in urls:
                p_a.append(toURLWithoutMeaninglessDiffs(url))

            _p = Page.select().where(Page.url.in_(p_a))
            f = list()

            for r in _p:
                f.append(r.toModel().url)

            new_urls = []
            for i in urls:
                if i in f:
                    logging.info("skipping {0}".format(i))
                else:
                    new_urls.append(i)

            logging.info('total {0} pages in this file'.format(len(urls)))

            urls = new_urls

            logging.info('{0} pages in this file that will be archived'.format(len(urls)))
        else:
            count = len(urls)
            logging.info('{0} pages in this file'.format(count))

        async def with_semaphore(url, semaphore):
            async with semaphore:
                if max_pages == None or self.d_c < max_pages:
                    pages = await self.savePage(url, conv = False)
                    self.d_c += 1

                    for p in pages:
                        self.items.append(p)

        sem = asyncio.Semaphore(max_semaphore)
        r = await asyncio.gather(
            *[with_semaphore(url, sem) for url in urls],
            return_exceptions=True
        )

        return self.items
