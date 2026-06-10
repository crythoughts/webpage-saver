from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Webdrivers.WebdriverPage import WebdriverPage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import logging

class Screenshot:
    def _get_path(self, page: WebPage, add: str = '1.jpeg'):
        return page.getThumbsDir().joinpath(add)

    async def make_viewport(self, page: WebPage, webdriver_page: WebdriverPage):
        try:
            await webdriver_page._page.screenshot(
                path = self._get_path(page, 'viewport.jpeg'),
            )
        except PlaywrightTimeoutError as e:
            logging.exception(e)
            page.has_screenshot = False

    async def make_fullscreen(self, page: WebPage, webdriver_page: WebdriverPage):
        try:
            await webdriver_page._page.screenshot(
                path=self._get_path(page, 'fullscreen.jpeg'), 
                full_page = True
            )
        except PlaywrightTimeoutError as e:
            logging.exception(e)
            page.has_screenshot = False
