from pathlib import Path
from pydantic import ValidationError
from peewee import *
from WebpageSaver import config
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Components.Utils import toURLWithoutMeaninglessDiffs
from yarl import URL
import logging
import json

db = SqliteDatabase(str(config.content.joinpath('cache.db')))

class BaseModel(Model):
    class Meta:
        database = db

class Page(BaseModel):
    title = TextField(default = 'Untitled')
    path_to = TextField(unique=True)
    taken_at = FloatField()
    is_redirect = BooleanField(default = 0)
    is_frame = BooleanField(default = 0)
    url = TextField()
    domain = TextField()
    data = TextField(null = False)

    @classmethod
    def fromModel(cls, model: WebPage, path_to: str):
        u = URL(model.url)

        new = Page()
        new.title = model.title
        new.path_to = path_to
        new.is_frame = int(model.is_iframe)

        if model.redirected_to != None:
            new.is_redirect = 1

        # Removing protocol and "//"
        new.url = toURLWithoutMeaninglessDiffs(model.url)

        if u.host.startswith('www.'):
            new.domain = u.host[4:]
        else:
            new.domain = u.host

        new.setData(model.model_dump(exclude_none = True, exclude_defaults = True))

        return new

    def setData(self, data: dict):
        self.taken_at = data.get('taken')
        self.data = json.dumps(data, ensure_ascii = False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        logging.info('indexated page {0}'.format(self.path_to))

    def toModel(self, fast: bool = True):
        if fast:
            try:
                m = WebPage.model_validate(json.loads(self.data))
                m.root_directory = config.webpages_dir
                return m
            except ValidationError as e:
                logging.exception(e)
                return WebPage(url = self.url, root_directory = str(config.webpages_dir))
        else:
            return WebPage.fromPath(self.path_to)

class Cache:
    '''
    List of webpages from data/webpages
    '''

    def __init__(self):
        db.connect()
        db.create_tables([Page])

        self.indexate()

    def getPages(self):
        return Page.select().order_by(Page.taken_at.desc())

    def getList(self):
        _list = config.get('webpages.list')
        if _list == None:
            return []

        return _list

    def indexate(self):
        paths = list()
        for path in Path(config.webpages_dir).rglob('*'):
            if path.name == 'data.json':
                paths.append(str(path.relative_to(config.webpages_dir).parent))

        ps = Page.select().where(Page.path_to.in_(paths))
        exist_paths = list()

        for item in ps:
            exist_paths.append(item.path_to)

        for path in paths:
            if path not in exist_paths:
                try:
                    p = WebPage.fromPath(path)
                    m = Page.fromModel(p, path)
                    m.save()
                except Exception as e:
                    logging.exception(e)
