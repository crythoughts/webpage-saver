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
                       conv: bool = True):
        # TODO: w selection
        crawler = Crawler()

        payload = list()
        webdriver = self.w_repo.getById(webdriver_id)
        await webdriver.start()

        page = WebPage(
            url = url
        )
        page.init(config.webpages_dir)

        fnl_page = await crawler.sendPage(page, webdriver, link_pages)

        if conv:
            payload.append(fnl_page.model_dump(exclude_none = True))
        else:
            payload.append(fnl_page)

        return payload

    # TODO rework
    async def savePageByHTML(self, url: str,
                            html: str, 
                            link_pages: list[WebPage] = None, 
                            title: str = None, 
                            remove_js: bool = True):
        crawler = Crawler()
        payload = list()
        webdriver = self.w_repo.getDefault()
        await webdriver.start()

        page = WebPage(
            url = url,
            from_html = True
        )
        page.init(config.webpages_dir)

        if link_pages:
            for p in link_pages:
                p.linkPage(page)
                p.saveData()
                page.linkPage(p)

        browser_page = await webdriver.openPage(page)

        await crawler.register(page, browser_page)
        await crawler.prepareTab(page, browser_page, url = url, html = html, remove_js = remove_js)
        await browser_page.goto(page.url)
        await browser_page.integrate(page)
        await crawler.crawl(page, browser_page)

        if title != None:
            page.title = title

        m = Page.fromModel(page, page.path_to)
        m.save()

        page.saveData()

        payload.append(page.model_dump(exclude_none = True))

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
                       find_by_start: bool = False
                       ):
        u = URL(url)

        # If URL is empty or not recognized as URL: Keywords search
        if url == '' or u.host == None:
            pages = Page.select()
            if url != '':
                pages = pages.where(Page.title.startswith(url))

            pages = pages.order_by(Page.taken_at.desc())
            res = list()

            for p in pages:
                m = p.toModel()
                if conv:
                    res.append(m.dump())
                else:
                    res.append(m)

            return {
                'type': 'keywords_search',
                'items': res
            }

        # Finding by start of the URL
        if find_by_start:
            pages = Page.select().where(Page.url.startswith(url)).group_by(Page.url).order_by(Page.taken_at.desc())
            res = list()

            for p in pages:
                m = p.toModel()
                if conv:
                    res.append(m.dump())
                else:
                    res.append(m)

            return {
                'type': 'urls',
                'items': res
            }

        # Thinking that it is a domain
        if u.path == '/':
            pages = Page.select().where(Page.domain == u.host).order_by(Page.taken_at.desc())
            res = list()

            for p in pages:
                m = p.toModel()
                if conv:
                    res.append(m.dump())
                else:
                    res.append(m)

            return {
                'type': 'domain_search',
                'items': res,
                'divided_by_months': [] # TODO
            }
        else:
            pages = Page.select().where(Page.url == u.human_repr()).order_by(Page.taken_at.desc())
            res = list()

            for p in pages:
                m = p.toModel()
                if conv:
                    res.append(m.dump())
                else:
                    res.append(m)

            return {
                'type': 'accurate_url',
                'items': res
            }
