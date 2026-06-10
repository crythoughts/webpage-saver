from pydantic import BaseModel, Field
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Components.GotRequest import GotRequest
from WebpageSaver.Crawler.Components.PageHTML import PageHTML
from typing import Any
from WebpageSaver import config
import asyncio
import logging
from urllib.parse import urlparse
from typing import AsyncGenerator
from playwright.async_api import Page as PlaywrightPage
from yarl import URL

class WebdriverPage:
    url_override: str = None
    got_assets: list[GotRequest]
    iframes: list
    iframe_pages: list[WebPage]

    _page: PlaywrightPage = None
    _page_response = None
    _first_request_ever = None

    def __init__(self):
        self.got_assets = []
        self.iframes = []
        self.iframe_pages = []

    async def goto(self, url: str, wait_until: str = 'commit'):
        _res = await self._page.goto(url, wait_until = wait_until)

        self._page_response = _res

    async def integrate(self, page: WebPage):
        page.base_url = self.get_base_url()
        page.relative_url = await self.get_relative_url()

    async def setTitle(self, page: WebPage):
        page.title = await self.get_title()

    async def close(self):
        await self._page.close()

    async def get_title(self):
        return await self._page.title()

    async def get_html(self):
        html_with_shadow = await self._page.evaluate("""
            () => {
                const extractShadowContent = (element) => {
                    let result = element.outerHTML;
                    
                    if (element.shadowRoot) {
                        const shadowHtml = Array.from(element.shadowRoot.children)
                            .map(child => extractShadowContent(child))
                            .join('');
                        result = result.replace('>', '><shadow-root>' + shadowHtml + '</shadow-root>');
                    }
                    
                    Array.from(element.children).forEach(child => {
                        const childHtml = extractShadowContent(child);
                        result = result.replace(child.outerHTML, childHtml);
                    });
                    
                    return result;
                };
                
                return extractShadowContent(document.documentElement);
            }
        """)

        return html_with_shadow
        #return await self._page.content()

    async def get_parsed_html(self):
        return PageHTML.from_html(await self.get_html())

    def get_url(self, orig: bool = False):
        _url = self.url_override
        if _url == None:
            _url = self._page.url

        if orig is True:
            return _url

        return urlparse(_url)

    def get_base_url(self):
        _url = self.get_url()
        return _url.scheme + '://' + _url.netloc

    async def get_relative_url(self):
        _base_url = await self._page.evaluate("""
                                              () => {return document.querySelector(\"base\") ? document.querySelector(\"base\").href : null}
                                              """)
        if _base_url == None:
            return self.get_base_url()

        return _base_url

    async def get_encoding(self) -> AsyncGenerator[str]:
        try:
            charset = await self._page.locator('meta[charset]')
            if charset:
                yield charset.get_attribute('charset')
        except:
            yield 'utf-8'

        try:
            content_type = await self._page.locator('meta[http-equiv=\"Content-Type\"]')
            if content_type:
                d = content_type.get_attribute('content')
                if 'charset=' in d:
                    yield content_type.split('charset=')[1].lower()
        except:
            yield 'utf-8'

        try:
            content_type = self._page_response.headers.get('content-type', '')
            if 'charset=' in content_type.lower():
                yield content_type.lower().split('charset=')[1].split(';')[0].strip()
            elif 'utf-8' in content_type.lower():
                yield 'utf-8'
        except Exception as e:
            logging.exception(e)

            yield 'utf-8'

    def override_url(self, url: str):
        self.url_override = url

    async def scroll_up(self):
        return await self._page.evaluate('() => window.scrollTo(0, 0);')

    async def scroll_down(self, scroll_cycles: int = 10, scroll_timeout: float = 0.1):
        last_height = await self._page.evaluate('() => {return document.body.scrollHeight}')
        scroll_iter = 0

        while True:
            if scroll_cycles != None:
                if scroll_iter > scroll_cycles:
                    break

            await self._page.evaluate('() => window.scrollTo(0, document.body.scrollHeight);')

            logging.info('scrolling down: {0}'.format(scroll_iter))

            await asyncio.sleep(scroll_timeout)

            new_height = await self._page.evaluate('() => {return document.body.scrollHeight}')
            if new_height == last_height:
                logging.info('scrolling down: height is not updating')

                break

            last_height = new_height
            scroll_iter += 1

    def get(self):
        return self._page

    def getStatus(self):
        return self._page_response.status

    def getResponseURL(self) -> str:
        return self._page_response.url

    def getFirstRequestEver(self):
        for item in self.got_assets:
            if item[1].is_first_ever == True:
                return item[1]

    def appendRequest(self, request: GotRequest, frame = None, page_link = None):
        f = None
        try:
            f = self.addFrame(frame, request, page_link)
        except Exception as e:
            logging.exception(e)

        if f != None:
            if URL(f.url) == URL(request.url):
                request.common_to_iframe = True

            request._frame = f

        self.got_assets.append((f, request))

    # Frames

    def addFrame(self, iframe, request, page_link):
        iframe_url = iframe.url
        # For some reason, the iframe html request may be located in empty frame
        if iframe_url == '':
            iframe_url = request.url

        if iframe == None:
            #print('wrong iframe', iframe_url, page_link.url)
            return None

        if URL(iframe_url) == URL(page_link.url):
            #print('iframe is the same page', iframe_url, page_link.url)
            return None

        if iframe_url in [None, 'about:blank']:
            #print('about:blank iframe', iframe_url, page_link.url)
            return None
            
        #found_iframe = None
        for f in self.iframe_pages:
            if URL(f.url) == URL(iframe_url):
                return f
                #break

        #if found_iframe != None:
        #    logging.info('iframe already added')
        #    return found_iframe

        self.iframes.append(iframe)

        wp = WebPage(
            is_iframe = True,
            url = iframe_url,
            common_page_id = page_link.identify,
            title = iframe.name,
            has_screenshot = False
        )
        wp.init(config.webpages_dir)
        wp.setURL(iframe_url)
        page_link.linked_iframe_pages.append(wp.identify)

        self.iframe_pages.append(wp)

        return wp

    def getFramePageByURL(self, url: str):
        for f in self.iframe_pages:
            if f.url == url:
                return f

    def getFramePages(self):
        for f in self.iframe_pages:
            yield f

    def getAdditionalPages(self): #getAdditionalPagesToSave
        for f in self.iframe_pages:
            yield f
