from pydantic import Field, BaseModel, computed_field
from typing import Any
from WebpageSaver import config
from playwright.async_api import Playwright, async_playwright
from WebpageSaver.Crawler.Components.UserAgent import UserAgent
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Webdrivers.WebdriverPage import WebdriverPage
from pathlib import Path
import logging
import aiohttp
import aiofiles
import zipfile

class Webdriver(BaseModel):
    _browser: Any = None
    id: int = Field(default = None)
    channel: str = Field(default = None)
    version: str = Field(default = None)
    platform: str = Field(default = 'win64')
    orig_url: str = Field(default = None)
    shell_path: str = Field()
    webdriver_type: str = Field(default = 'chromedriver')
    user_data_dir: str = Field(default = None)
    user_agent: str = Field(default = None)

    async def start(self):
        if self.is_running == True:
            return None

        size = None
        #if i.get('webdriver.sizes') != None:
        #    size = i.get('webdriver.sizes').split(',')

        self._playwright = await async_playwright().start()

        logging.info('launching browser')

        try:
            if size != None:
                self.viewport = {"width": int(size[0]), "height": int(size[1])}
        except Exception as e:
            logging.info(e)

        self._browser = await self._launch_browser()
        self._context = await self._browser.new_context(
            #viewport = self.viewport,
            user_agent = self.getUserAgentString(),
        )

    async def _launch_browser(self):
        #i.get('webdriver.headless')
        is_headless = False
        args = [
            '--start-maximized',
            '--start-fullscreen',
            '--headless',
            '--no-sandbox',
            '--user-agent={0}'.format(self.getUserAgentString())
        ]

        if self.user_data_dir != None:
            args.append('--user_data=' + self.user_data_dir)

        #for argument in i.get('webdriver.args'):
        #    args.append(argument)

        return await self._playwright.chromium.launch(
            executable_path = self.getHeadlessShell(),
            args = args,
            headless = is_headless
        )

    @computed_field
    @property
    def is_running(self) -> bool:
        return self._browser != None

    def getUserAgentString(self) -> str:
        '''
        Returns UserAgent string.
        '''

        if self.user_agent:
            return self.user_agent

        _passed = config.get('web.crawler.user_agent')
        if _passed == None:
            return UserAgent.generate().string

        return _passed.string

    def getHeadlessShell(self) -> Path:
        if Path(self.shell_path).is_relative_to(config.drivers):
            return config.drivers.joinpath(self.shell_path)
        else:
            return self.shell_path

    async def stop(self):
        '''
        Stops browser emulator.
        '''
        for i in ['_context', '_browser', '_playwright']:
            if hasattr(self, i):
                if i != '_playwright':
                    getattr(self, i).close()
                setattr(self, i, None)

        self._playwright = None

    async def openPage(self, page: WebPage):
        new_page = WebdriverPage()
        new_page._page = await self._context.new_page()
        '''new_page._page.add_init_script("""
            Element.prototype._attachShadow = Element.prototype.attachShadow;
            Element.prototype.attachShadow = function(init) {
                return this._attachShadow({...init, mode: 'open'});
            };
        """)'''

        logging.info('opened page {0}'.format(page.url))
        #await page.setViewport(self.viewport)

        return new_page

    def getShell(self):
        if self.webdriver_type == 'chromedriver':
            return self.executable_path.joinpath('chrome').joinpath('chrome-headless-shell.exe')

    async def downloadFromOrigURL(self):
        dirs = config.drivers
        self_dir = dirs.joinpath('{0}_{1}_{2}'.format(self.webdriver_type, self.platform, self.version))

        assert self_dir.exists() == False

        self_dir.mkdir()
        filename = 'chrome-headless-shell-win64.zip'
        zip_file = self_dir.joinpath(filename)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.orig_url) as response:
                async with aiofiles.open(str(zip_file), mode='wb') as f:
                    async for chunk in response.content.iter_chunked(4096):
                        await f.write(chunk)

        with zipfile.ZipFile(str(zip_file), 'r') as zip_ref:
            #_names = zip_ref.namelist()
            zip_ref.extractall(self_dir)

        #self_dir.rename(shell)

        zip_file.unlink()

        self.shell_path = str(zip_file.relative_to(config.drivers))
