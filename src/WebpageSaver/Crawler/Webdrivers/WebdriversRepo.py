from WebpageSaver import config
from typing import Generator
from WebpageSaver.Crawler.Webdrivers.Webdriver import Webdriver
import aiohttp
import platform
import logging

class WebdriversRepo:
    _list: list
    _i: int = 0

    def __init__(self):
        self._list = list(self._getAll())

    def _getWebdriversList(self):
        return self._list

    def _getCurrentWebdriverIndex(self):
        return config.get('webdrivers.current', 0)

    def _setCurrentWebdriverIndex(self, id: int):
        config.set('webdrivers.current', id)

    def _getAll(self) -> Generator[Webdriver]:
        _list = config.get('webdrivers')
        if _list == None or type(_list) != list:
            return []

        for i in _list:
            w = Webdriver.model_validate(i)
            w.id = self._i
            self._i += 1
            yield w

    def getAll(self):
        return self._list

    def getDefault(self) -> Webdriver:
        return list(self.getAll())[self._getCurrentWebdriverIndex()]

    def add(self, webdriver: Webdriver):
        similar = None
        _list = list(self.getAll())
        for w in _list:
            if w.shell_path == webdriver.shell_path:
                similar = w

            logging.info('want to notice: webdriver with name {0} already exist'.format(w.shell_path))
            break

        if similar == None:
            webdriver.id = self._i
            new_list = list()

            for i in _list + [webdriver]:
                new_list.append(i.model_dump(exclude_none = True, exclude_computed_fields = True, exclude_defaults = True))

            config.set('webdrivers', new_list)
            self._list.append(webdriver)
            self._setCurrentWebdriverIndex(len(new_list) - 1)
        else:
            self._setCurrentWebdriverIndex(_list.index(w))

        self._i += 1

    async def get_versions(self):
        version = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

        async with aiohttp.ClientSession() as session:
            async with session.get(version) as response:
                channels = await response.json()

        return channels.get('channels')

    def getPlatform(self):
        version = ['', '']
        system_type = platform.system().lower()
        architecture = platform.machine().lower() 

        if architecture in ['x86_64', 'amd64']:
            version[1] = '64'
        elif architecture in ['i386', 'i686', 'x86']:
            version[1] = '32'
        elif architecture in ['arm64', 'aarch64']:
            version[1] = 'arm64'
        else:
            version[1] = architecture

        match system_type:
            case "darwin":
                if architecture in ['arm64', 'aarch64']:
                    version[1] = "arm64"
                else:
                    version[1] = "x64"

                version[0] = 'mac-'
            case "windows":
                version[0] = 'win'
            case _:
                version[0] = 'win'

        return ''.join(version)
