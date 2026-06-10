from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Webdrivers.WebdriverPage import WebdriverPage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
#from WebpageSaver.Crawler.Components.Increment import Increment
from WebpageSaver.Crawler.Components.Canvas import Canvas
from pathlib import Path
import logging
import base64

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

    async def make_canvases(self, page: WebPage, webdriver_page: WebdriverPage):
        canvases = await webdriver_page._page.query_selector_all('canvas')
        payload = {}
        #canv = Increment()
        for index, canvas in enumerate(canvases):
            try:
                canvas_id = f"canvas_{index}"

                await canvas.evaluate(f"(el, id) => el.setAttribute('{page.getOrigAttr()}', id)", canvas_id)
                screenshot_data = await canvas.evaluate("""
                    (canvas) => {
                        return canvas.toDataURL('image/jpeg', 0.8);
                    }
                """)

                filepath = page.getThumbsDir().joinpath(f"{canvas_id}.jpeg")

                with open(str(filepath), 'wb') as f:
                    #f.write(await canvas.screenshot(timeout = 5000, type='jpeg',))
                    f.write(base64.b64decode(screenshot_data.split(',')[1]))

                canvas_info = await canvas.evaluate("""
                    (el) => ({
                        width: el.width,
                        height: el.height,
                        className: el.className,
                        id_attribute: el.id || null
                    })
                """)

                payload[canvas_id] = Canvas(**{
                    'id': canvas_id,
                    **canvas_info
                })

                logging.info('screenshoted ' + canvas_id)
            except Exception as e:
                logging.error(e)

        return payload
