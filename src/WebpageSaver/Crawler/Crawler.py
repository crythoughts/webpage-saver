from WebpageSaver.Crawler.Components.GotRequest import GotRequest
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Webdrivers.WebdriverPage import WebdriverPage
from WebpageSaver.Crawler.Screenshot import Screenshot
from WebpageSaver.Crawler.Components.Increment import Increment
from WebpageSaver.Crawler.Components.PageHTML import PageHTML
from WebpageSaver.Crawler.Assets.Asset import Asset
from WebpageSaver.Cache import Cache, Page
from datetime import datetime
from yarl import URL
from WebpageSaver import config
import asyncio
import logging

class Crawler:
    non_request_downloads: bool = False

    async def register(self, page: WebPage, webdriver_page):
        self.i = Increment()

        logging.info('registering page...')

        _orig_dir = page.getAssetsDir()

        async def _request(request):
            if URL(page.url) == URL(request.url):
                logging.info('not downloading page again')
                return

            logging.info('{0} asset'.format(request.url))

            webdriver_page.got_assets.append(GotRequest(
                url = request.url,
                started_at = datetime.now().timestamp(),
                request = request,
                done = False
            ))

        async def _response(response):
            request = None
            for item in webdriver_page.got_assets:
                if item.url_matches(response.url):
                    request = item

            if request == None:
                return

            logging.info('request {0}, method {1}'.format(response.url, request.request.method))

            if request.request.method == 'GET':
                try:
                    _url = response.url
                    if request.request.redirected_from:
                        logging.info('assets: redirected from {0}'.format(_url))
                        _url_r = request.request.redirected_from.url
                        for _item in webdriver_page.got_assets:
                            if _item.url_matches(_url_r):
                                request = _item

                    request.asset = Asset(url=_url)
                    _i = self.i.getIndex()
                    #_dir = _orig_dir.joinpath(request.asset.getEncodedURL())
                    page.addAsset(_i, request)
                    #page.assets_links[request.asset.getEncodedURL()] = _i

                    headers = response.headers
                    request.content_type = headers.get('content-type')
                    _dir = _orig_dir.joinpath(str(_i))
                    buffer = await response.body()
                    with open(str(_dir), 'wb+') as _file:
                        _file.write(buffer)

                    request.ended_at = datetime.now().timestamp()

                    logging.info('assets: downloaded {0}'.format(_url))
                except Exception as e:
                    logging.error('error downloading asset {0}'.format(_url))
                    logging.exception(e)

            request.done = True

        webdriver_page._page.on('request', _request)
        webdriver_page._page.on('response', _response)

    async def prepareTab(self, page: WebPage, webdriver_page, url: str, html: str, remove_js: bool = True):
        #await webdriver_page._page.evaluate("() => {document.write(`"+html+"`);}")
        await webdriver_page._page.evaluate("() => {open = null; location.replace = null; history = null; location.reload = null; location.assign = null;}")
        await webdriver_page._page.evaluate("() => {xhr = null; fetch = null;}")

        _p = PageHTML.from_html(html)
        _p.remove_integrity()

        if remove_js:
            _p.clear_js(softly = True)

        async def handle_route(route, request):
            if URL(request.url) == URL(url):
                await route.fulfill(
                    status=200,
                    content_type="text/html",
                    body=_p.prettify()
                )
                return
            else:
                await route.continue_()

        await webdriver_page._page.route(url, handle_route)

    async def crawl(self, 
                    page: WebPage, 
                    webdriver_page: WebdriverPage,
                    scroll_down: bool = True,
                    scroll_down_max_cycles: int = 5,
                    download_assets: bool = True,
                    remove_scripts: bool = False,
                    make_screenshots: bool = True,
                    sleep_before_crawl: float = 0,
                    sleep_before_getting_html: float = 0,
                    sleep_network_timeout: float = 0):

        u = URL(page.url)
        await webdriver_page.integrate(page)
        await asyncio.sleep(sleep_before_crawl)

        async for e in webdriver_page.get_encoding():
            page.addEncoding(e)

        await webdriver_page.scroll_up()

        if make_screenshots:
            await Screenshot().make_viewport(page, webdriver_page)

        if scroll_down:
            if u.fragment not in ['', None]:
                await webdriver_page.scroll_down(scroll_down_max_cycles)

        await asyncio.sleep(sleep_before_getting_html)
        await webdriver_page._page.wait_for_timeout(sleep_network_timeout)

        if make_screenshots:
            await Screenshot().make_fullscreen(page, webdriver_page)

        html = await webdriver_page.get_parsed_html()
        page.setEncoding(html.encoding)

        for meta in html.get_meta(page):
            page.meta.append(meta)

        results = dict()
        for key in ['get_favicons', 'get_media', 'get_downloadable_links', 'get_scripts']:
            if results.get(key) == None:
                results[key] = list()

            logging.info('getting {0}...'.format(key[4:]))

            for item in getattr(html, key)(page):
                found_asset = None

                match (key):
                    case 'get_scripts':
                        if remove_scripts:
                            item.decompose()
                            continue

                for asset in webdriver_page.got_assets:
                    if item.url and asset.url_matches(item.url):
                        found_asset = asset

                if self.non_request_downloads and found_asset == None and item.has_url():
                    if download_assets == False:
                        continue

                    try:
                        await item.download_function(page.getAssetsDir(), str(self.i.getIndex()))
                        logging.info(key + ': non-request download: ' + item.get_url())
                        #print(item, found_asset)
                    except Exception as e:
                        logging.exception(e)

                try:
                    item.moveUrlToAnotherAttr(page)
                    results[key].append(item)
                except Exception as e:
                    logging.exception(e)

        for link in results.get('get_favicons'):
            page.favicons.append(link)

        if remove_scripts:
            try:
                html.clear_js()
            except Exception as e:
                logging.exception(e)

        page._create_index()
        page.write(html.prettify())
        page.saveData()

        #await self._after_crawl(page)

    async def _after_crawl(self, page: WebPage):
        pass

    async def sendPage(self, page: WebPage, webdriver, link_pages: list[WebPage]):
        if link_pages:
            for p in link_pages:
                p.linkPage(page)
                p.saveData()
                page.linkPage(p)

        got_page = None
        has_redir = False

        browser_page = await webdriver.openPage(page)
        await self.register(page, browser_page)
        await browser_page.goto(page.url)

        # After "GOTO"
        # It will skip other stages of redirect (if they are more than 1), but anyway.
        if str(browser_page.getStatus())[0] == '3':
            logging.log('URL redirected')

            got_page = WebPage(
                url = browser_page.getResponseURL(),
                title = 'Redirect',
                status = 200, # ig
                identify = page.identify
            )
            got_page.init(config.webpages_dir)
            #got_page.linkPage(page)
            page.linkPage(got_page)
            has_redir = True
        else:
            got_page = page
            got_page.status = browser_page.getStatus()

        await browser_page.integrate(page)
        await self.crawl(page, browser_page)

        if has_redir == True:
            self._savePageToCache(page)

        self._savePageToCache(got_page)

        return got_page

    def _savePageToCache(self, page: WebPage):
        m = Page.fromModel(page, page.path_to)
        m.save()
        page.saveData()
