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
import aiofiles

class Crawler:
    non_request_downloads: bool = False
    optional_sleep_s: float = 0
    page_load_timeout_s: int = 5
    sleep_before_crawl_s: float = 0
    make_screenshots: bool = True

    async def register(self, page: WebPage, webdriver_page):
        self.i = Increment()

        logging.info('registering page...')

        async def _request(request):
            try:
                is_first_ever = False
                #print(request.url)

                if URL(page.url) == URL(request.url):
                    #logging.info('not downloading page again')
                    is_first_ever = True
                    #return

                logging.info('{0} asset'.format(request.url))

                webdriver_page.appendRequest(GotRequest(
                    url = request.url,
                    started_at = datetime.now().timestamp(),
                    request = request,
                    done = False,
                    is_first_ever = is_first_ever
                ), frame = request.frame,
                page_link = page)
            except Exception as e:
                logging.exception(e)

        async def _response(response):
            __request = None
            for item in webdriver_page.got_assets:
                if item[1].url_matches(response.url):
                    __request = item[1]

            if __request == None:
                return

            __request.response = response

            logging.info('request {0}, method {1}'.format(response.url, __request.request.method))

            if __request.common_to_iframe:
                logging.info('request is common to its iframe')

                # Writing as index.html!
                __request._frame._create_index()
                text = await response.body()
                __request._frame.write(text)
                #async with aiofiles.open(page.getRootFile(), mode='wb') as f:
                #    async for chunk in response.content.iter_chunked(4096):
                #        await f.write(chunk)

                __request.done = True

            if __request.done == False and __request.is_first_ever == False and __request.request.method == 'GET':
                try:
                    _url = response.url
                    if __request.request.redirected_from:
                        logging.info('assets: redirected to {0}'.format(_url))
                        _url_r = __request.request.redirected_from.url
                        for _item in webdriver_page.got_assets:
                            if _item[1].url_matches(_url_r):
                                __request = _item[1]

                    __request.asset = Asset(url=_url)
                    __request.status = response.status
                    _i = self.i.getIndex()
                    #_dir = _orig_dir.joinpath(request.asset.getEncodedURL())

                    if __request._frame:
                        __request._frame.addAsset(_i, __request)
                        page.addAsset(_i, __request)
                    else:
                        page.addAsset(_i, __request)
                    #page.assets_links[request.asset.getEncodedURL()] = _i

                    headers = response.headers
                    __request.content_type = headers.get('content-type')
                    _orig_dir = page.getAssetsDir()

                    if __request._frame != None:
                        _w = webdriver_page.getFramePageByURL(__request._frame.url)

                        if _w != None:
                            _orig_dir = _w.getAssetsDir()
                        else:
                            logging.error('something wrong with iframe')

                    dir_to_download = _orig_dir.joinpath(str(_i))

                    buffer = await response.body()
                    with open(str(dir_to_download), 'wb+') as _file:
                        _file.write(buffer)

                    logging.info('assets: downloaded {0}'.format(_url))
                except Exception as e:
                    logging.error('error downloading asset {0}'.format(_url))
                    logging.exception(e)

            __request.ended_at = datetime.now().timestamp()
            __request.done = True

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
                    remove_scripts: bool = False):

        u = URL(page.url)
        await webdriver_page.integrate(page)

        if self.sleep_before_crawl_s > 0:
            await asyncio.sleep(self.sleep_before_crawl_s)

        async for e in webdriver_page.get_encoding():
            page.addEncoding(e)

        await webdriver_page.scroll_up()

        try:
            await webdriver_page._page.wait_for_event('domcontentloaded', timeout = self.page_load_timeout_s * 1000)
        except Exception as e:
            logging.exception(e)

        if self.make_screenshots:
            await Screenshot().make_viewport(page, webdriver_page)

        if scroll_down:
            if u.fragment not in ['', None]:
                await webdriver_page.scroll_down(scroll_down_max_cycles)

        if self.optional_sleep_s > 0:
            await asyncio.sleep(self.optional_sleep_s)

        #await webdriver_page._page.wait_for_timeout(sleep_network_timeout)

        if self.make_screenshots:
            await Screenshot().make_fullscreen(page, webdriver_page)

        page.canvases = await Screenshot().make_canvases(page, webdriver_page)

        html = await webdriver_page.get_parsed_html()
        page.setEncoding(html.encoding)
        await webdriver_page.setTitle(page)

        for meta in html.get_meta(page):
            page.meta.append(meta)

        results = dict()
        suggested_content_type = None
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
                    if item.url and asset[1].url_matches(item.url):
                        found_asset = asset[1]

                should_download = self.non_request_downloads and found_asset == None and item.has_url()
                if key == 'get_favicons':
                    should_download = True
                    suggested_content_type = 'image/x-icon'

                if should_download:
                    if download_assets == False:
                        continue

                    try:
                        _ids = self.i.getIndex()
                        req = await item.download_function(page.getAssetsDir(), str(_ids))

                        logging.info(key + ': non-request download: ' + item.get_url())

                        if suggested_content_type != None:
                            req.content_type = suggested_content_type

                        page.addAsset(_ids, req)
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

    async def sendPage(self, page: WebPage, 
                       webdriver, 
                       link_pages: list[WebPage],
                       remove_js: bool = False,
                       html: str = None,
                       from_html: bool = False):
        if link_pages:
            for p in link_pages:
                p.linkPage(page)
                p.saveData()
                page.linkPage(p)

        redir_page = None

        browser_page = await webdriver.openPage(page)
        #browser_page._page.set_default_timeout()
        await self.register(page, browser_page)

        if from_html:
            await self.prepareTab(page, browser_page, url = page.url, html = html, remove_js = remove_js)

        await browser_page.goto(page.url)

        # After "GOTO"
        # It will skip other stages of redirect (if they are more than 1), but anyway.
        #print(browser_page.getFirstRequestEver())

        status = 200

        try:
            status = browser_page.getFirstRequestEver().response.status
        except Exception as e:
            logging.exception(e)

        if str(status)[0] == '3':
            logging.info('URL redirected')

            redir_page = WebPage(
                url = str(page.url),
                title = 'Redirect',
                status = status, # ig
                redirected_to = page.identify,
                has_screenshot = False
            )
            redir_page.init(config.webpages_dir)
            #page.linkPage(page)
            page.url = browser_page.getResponseURL()
            page.linkPage(redir_page)

        page.status = browser_page.getStatus()

        await browser_page.integrate(page)
        await self.crawl(page, browser_page)

        self._savePageToCache(page)

        if redir_page != None:
            self._savePageToCache(redir_page)

        for p in browser_page.getAdditionalPages():
            self._savePageToCache(p)

        return page

    def _savePageToCache(self, page: WebPage):
        m = Page.fromModel(page, page.path_to)
        m.save()
        page.saveData()
