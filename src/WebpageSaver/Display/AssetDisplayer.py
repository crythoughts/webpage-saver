from aiohttp import web
from WebpageSaver import config

class AssetDisplayer:
    def getResponseByContentType(self, content_type: str):
        if content_type != None:
            if 'image/' in content_type:
                return web.FileResponse(config.cwd.joinpath('web').joinpath('static').joinpath('no_asset.jpg'))

            if 'json' in content_type:
                return web.json_response({})

        return web.HTTPNotFound()

asset_displayer = AssetDisplayer()
