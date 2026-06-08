from pathlib import Path
import json
import logging

class Config:
    def __init__(self):
        self.cwd = Path.cwd()
        self.parent = self.cwd.parent
        self.data = self.parent.joinpath('data')
        self.data.mkdir(exist_ok=True)
        self.content = self.data.joinpath('content')
        self.content.mkdir(exist_ok=True)
        self.drivers = self.data.joinpath('drivers')
        self.drivers.mkdir(exist_ok=True)

        self._setothers()

        self.file = self.data.joinpath('conf.json')
        #self.cache = self.data.joinpath('cache.json')
        if self.file.exists() == False:
            tmp = open(str(self.file), 'w', encoding = 'utf-8')
            default_settings = dict()

            json.dump(default_settings, tmp)
            tmp.close()

        self._stream = open(self.file, 'r+', encoding='utf-8')
        self.updateFromFile()

        if self.get('pages_dir'):
            self.content = Path(self.get('pages_dir'))
            assert self.content.is_dir() and self.content.exists(), 'not a dir or not exists.'
            self._setothers()

    def _setothers(self):
        self.webpages_dir = self.content.joinpath('webpages')
        self.webpages_dir.mkdir(exist_ok=True)

    def __del__(self):
        try:
            self._stream.close()
        except AttributeError:
            pass

    def updateFile(self) -> None:
        self._stream.seek(0)

        json.dump(self.values, self._stream, indent=4, ensure_ascii=False)

        self._stream.truncate()

    def updateFromFile(self):
        try:
            self.values = json.load(self._stream)
        except json.JSONDecodeError:
            logging.error("failed to load conf.json")

    def reset(self) -> None:
        self._stream.seek(0)
        self._stream.write("{}")
        self._stream.truncate()

        self.values = {}

    def get(self, option: str, default: str = None):
        got = self.values.get(option)
        if got == None:
            return default

        return got

    def set(self, option: str, value: str):
        if value == None:
            del self.values[option]
        else:
            self.values[option] = value

        self.updateFile()

config = Config()
