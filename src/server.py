from WebpageSaver.API import API
from WebpageSaver.Crawler.Assets.Asset import Asset
from aiohttp import web
from WebpageSaver import config
from WebpageSaver.Crawler.Components.PageHTML import PageHTML
from pathlib import Path
from datetime import datetime
import asyncio
import logging
import aiohttp_jinja2
import jinja2
import urllib

api = API()
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
}

routes = web.RouteTableDef()

def check_path(maximum_directory: Path, path: Path):
    path.absolute().relative_to(maximum_directory.resolve())

    if not path.exists():
        raise FileNotFoundError()

    if not path.is_file():
        raise FileNotFoundError()

@routes.get('/')
def ip(request: web.Request):
    return aiohttp_jinja2.render_template('@index.html',request,{})

@routes.get('/page')
async def gpbid_wmi(request: web.Request):
    query = request.rel_url.query

    url = '/page/' + query.get('id') + '?r=1'
    for key, val in query.items():
        if key in ['id']:
            continue

        url += '&' + key + '=' + val

    return web.HTTPFound(location = url)

@routes.get('/page/{id:.*}')
async def gpbid(request: web.Request):
    query = dict(request.rel_url.query)
    page_id = request.match_info.get('id')
    mode = query.get('mode', 'page')

    if mode not in ['page', 'page_options', 'text', 'all_assets', 'url', 'meta', 'metatags', 'media', 'hyperlinks']:
        return web.HTTPNotFound(body = 'Invalid mode')

    pages = api.getPagesById(ids = [page_id], convert = False)
    if len(pages) == 0:
        return web.Response(status = 404)

    page = pages[0]
    # Encoding
    encoding = page.encoding
    if query.get('encoding') != None:
        encoding = query.get('encoding')

    match (mode):
        # Page display
        case 'page' | 'text':

            if mode == 'text':
                query['remove_scripts'] = 'on'
                query['remove_inline_css'] = 'on'
                query['remove_styles'] = 'on'
                query['remove_iframes'] = 'on'
                query['remove_meta'] = 'on'
                query['remove_selectors'] = 'nav, header, input, button'

            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)

            if query.get('remove_scripts') == 'on':
                html.clear_js()
            if query.get('remove_inline_css') == 'on':
                html.remove_inline_css()
                html.remove_html_stylization()
            if query.get('remove_styles') == 'on':
                html.remove_css()
            if query.get('remove_iframes') == 'on':
                html.remove_iframes()
            if query.get('remove_meta') == 'on':
                html.remove_meta()

            try:
                if query.get('remove_selectors') != None:
                    html.remove_selectors(query.get('remove_selectors'))
            except:
                pass

            if query.get('original') != 'on':
                html.make_correct_links(page)

            html.trivia()
            #head_html = html.move_head()

            return web.Response(
                body = html.prettify(encoding = encoding), 
                content_type='text/html',
                charset = encoding
            )

        case 'page_options':

            return aiohttp_jinja2.render_template('page_options.html', request, {
                'page': page,
                'id': page_id,
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'meta':

            return aiohttp_jinja2.render_template('page_info.html', request, {
                'page': page,
                'taken': page.getReadableTaken(),
                'linked': page.getLinkedPages()
            })

        case 'url':
            p_url = query.get('url')
            new_url = Asset.getDecodedURL(p_url)
            redirect_url = page.getRelativeURL(new_url)

            return aiohttp_jinja2.render_template('url.html', request, {
                'url': redirect_url,
                'id': page.identify,
                'back_btn': '/page/' + page_id
            })

        case 'all_assets':

            return aiohttp_jinja2.render_template('all_assets.html', request, {
                'assets': page.getAssets(),
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'metatags':

            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)

            return aiohttp_jinja2.render_template('metatags.html', request, {
                'metatags': page.meta,
                'links': html.get_links(page),
                'scripts': html.get_scripts(page),
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'media':

            mmode = query.get('mmode')
            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)
            if query.get('original') != 'on':
                html.make_correct_links(page, remove_temporary_attrs = False)

            selectors = None

            match (mmode):
                case 'all':
                    selectors = '[src]'
                case 'img':
                    selectors = 'img[src]'
                case 'video':
                    selectors = 'video[src]'
                case 'audio':
                    selectors = 'audio[src]'

            medias = html.get_media(page, selectors, set_local_urls = True)

            return aiohttp_jinja2.render_template('media.html', request, {
                'media': medias,
                'mmode': mmode,
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'hyperlinks':

            rel = query.get('rel', 'off')

            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)
            if rel == 'on':
                html.make_correct_links(page)

            return aiohttp_jinja2.render_template('hyperlinks.html', request, {
                'urls': html.get_urls(page, keep_original_urls = rel == 'off'),
                'page': page,
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

@routes.get('/page/asset')
async def gpa(request: web.Request):
    page_id = request.rel_url.query.get('id')
    asset_url = request.rel_url.query.get('asset_url', None)
    path_id = request.rel_url.query.get('path', '')
    #path_id = urllib.parse.unquote(path_id)

    pages = api.getPagesById(ids = [page_id], convert = False)
    if len(pages) == 0:
        return web.HTTPNotFound(body = 'Not found page')

    page = pages[0]
    req = None

    if asset_url != None:
        _ = page.getAssetByUrl(asset_url)
        path_id = _[0]
        req = _[1]
    else:
        req = page.getAssetById(path_id)

    if req == None:
        return web.HTTPNotFound(body = 'Not found asset')

    path = page.getAssetPathById(path_id)
    file_name = req.asset.getName()

    #decode_path = request.query.get('d') == '1'
    #if decode_path:
    #    path = base64.urlsafe_b64decode(path.encode('utf-8')).decode()

    assets_path = page.getAssetsDir()
    file: Path = assets_path.joinpath(path)

    try:
        check_path(assets_path, file)
    except (ValueError, RuntimeError) as e:
        logging.exception(e)
        return web.HTTPForbidden(reason="Access denied")

    if not file.is_file():
        return web.HTTPNotFound(text="Not found file")

    h = {
        'Content-Disposition': f'inline; filename="{file_name}"',
        'Content-Type': req.getContentType(),
    }

    #if asset_url != None:
    #    h.update(cors_headers)

    return web.FileResponse(str(file), headers = h)

@routes.get('/page/screenshot')
def gpsbid(request):
    page_id = request.rel_url.query.get('id')
    filename = request.rel_url.query.get('file')
    pages = api.getPagesById(ids = [page_id], convert = False)

    if len(pages) == 0:
        return web.HTTPNotFound(body = 'Not found page')

    page = pages[0]
    screenshot = page.getThumbsDir().joinpath(filename)

    try:
        check_path(page.getThumbsDir(), screenshot)
    except (ValueError, RuntimeError) as e:
        logging.exception(e)
        return web.HTTPForbidden(reason="Access denied")

    return web.FileResponse(str(screenshot), headers = {
        'Content-Type': 'image/jpeg'
    })

@routes.get('/save')
def spw(request: web.Request):
    return aiohttp_jinja2.render_template('save.html',request,{})

@routes.get('/page/search')
def sfp(request: web.Request):
    query = request.rel_url.query
    q = query.get('q', '')

    res = api.findPagesByURL(url = q, conv = False)
    search_type = res.get('type')

    return aiohttp_jinja2.render_template('search.html',request,{
        'q': q,
        'items': res.get('items'),
        'search_type': search_type
    })

@routes.get('/webdrivers')
def sfp(request: web.Request):

    return aiohttp_jinja2.render_template('webdrivers.html',request,{
        'items': api.getWebdrivers(conv = False),
        'current_index': api.w_repo._getCurrentWebdriverIndex()
    })

@routes.get('/api/webdrivers')
async def gw(request: web.Request):
    return web.json_response(api.getWebdrivers())

'''
@routes.get('/api/webdrivers/get_chromedrivers')
async def gc(request: web.Request):
    return web.json_response(await api.getAvailableWebdrivers())
'''

@routes.post('/api/webdrivers/download')
async def gc(request: web.Request):
    query = request.rel_url.query
    channel = query.get('channel', 'Stable')

    assert channel != None and channel in ['Stable', 'Beta', 'Canary', 'Dev']

    w = await api.getAvailableWebdrivers()
    c = w.get(channel)

    try:
        v = await api.webdriverFromChannel(c)
    except AssertionError:
        raise web.HTTPConflict(body = 'Webdriver already downloaded')

    return web.json_response(v.model_dump(exclude_none = True, exclude_defaults=True))

@routes.patch('/api/webdrivers/stop')
async def gw(request: web.Request):
    query = request.rel_url.query
    ids = int(query.get('id'))
    ws = api.getWebdrivers(conv = False)
    w = None

    try:
        w = ws[ids]
    except:
        raise web.HTTPNotFound()

    await w.stop()

    return web.json_response({
        'res': 1
    })

@routes.put('/api/webdrivers/setDefault')
async def gw(request: web.Request):
    query = request.rel_url.query
    ids = int(query.get('id'))
    ws = api.getWebdrivers(conv = False)
    w = None

    try:
        w = ws[ids]
    except:
        raise web.HTTPNotFound()

    api.w_repo._setCurrentWebdriverIndex(w.id)

    return web.json_response({
        'res': 1
    })

@routes.delete('/api/webdriver')
async def gw(request: web.Request):
    query = request.rel_url.query
    ids = int(query.get('id'))
    ws = api.getWebdrivers(conv = False)
    w = None

    try:
        w = ws[ids]
    except:
        raise web.HTTPNotFound()

    w.delete()

    return web.json_response({
        'res': 1
    })

@routes.post('/api/pages/save')
async def sp(request: web.Request):
    inputs = await request.post()
    url = inputs.get('url')
    ps = None
    link_to = inputs.get('link_to')

    if link_to != None:
        ps = api.getPagesById(ids = [link_to], convert = False)

        if len(ps) == 0:
            raise web.HTTPNotFound(body = 'Not found page to link')

    try:
        payload = await api.savePage(url = url, link_pages = ps)
    except Exception as e:
        raise web.HTTPBadRequest(body = str(e), status = 500)

    return web.json_response(payload, headers = cors_headers)

@routes.post('/api/pages/html_save')
async def sp(request: web.Request):
    inputs = await request.post()
    html = inputs.get('html')
    url = inputs.get('url')
    remove_js = int(inputs.get('remove_js')) == 1
    link_to = inputs.get('link_to')
    title = inputs.get('title')

    ps = None

    if link_to != None:
        ps = api.getPagesById(ids = [link_to], convert = False)

        if len(ps) == 0:
            return web.HTTPNotFound(body = 'Not found page to link')

    try:
        payload = await api.savePageByHTML(url = url,
                                           html = html,
                                           link_pages = ps,
                                           title = title,
                                           remove_js = remove_js
        )
    except Exception as e:
        raise web.HTTPBadRequest(body = str(e))

    return web.json_response(payload, headers = cors_headers)

@routes.options('/api/pages/html_save')
@routes.options('/api/pages/save')
#@routes.options('/page/asset')
async def sp(request: web.Request):
    return web.Response(
        text = None,
        content_type = 'application/json',
        headers = cors_headers
    )

@routes.get('/api/pages')
async def gp(request: web.Request):
    page_id = request.rel_url.query.get('id')
    if page_id != None:
        return web.json_response(api.getPagesById(ids = [page_id]))

    return web.json_response(api.getPages())

@routes.delete('/api/page')
async def dpbid(request: web.Request):
    page_id = request.rel_url.query.get('id')
    api.deletePagesById(ids = [page_id])

    return web.json_response({'success': 1})

@routes.patch('/api/page')
async def epbid(request: web.Request):
    page_id = request.rel_url.query.get('id')
    new_taken = request.rel_url.query.get('new_taken')
    #new_name = request.rel_url.query.get('new_name')
    #new_url = request.rel_url.query.get('new_url')
    api.editPageById(ids = [page_id], new_taken = new_taken)

    return web.json_response({'success': 1})

@routes.get('/sw.js')
def swjs(request: web.Request):
    return web.FileResponse(
        config.cwd.joinpath('web').joinpath('static').joinpath('sw-replace.js'),
        headers = {
            'Service-Worker-Allowed': '/',
            'Cache-Control': 'no-cache',
        }
    )

async def main():
    host = config.get('server.host', '127.0.0.1')
    port = config.get('server.host', 7514)

    app = web.Application()
    aiohttp_jinja2.setup(app,
        loader=jinja2.FileSystemLoader(config.cwd.joinpath('web').joinpath('templates')))

    app.router.add_routes(routes)
    app.router.add_static('/static/', path='./web/static', name='static')

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host = host,
        port = port
    )

    await site.start()

    logging.info('server opened on {0}:{1}'.format(host, port))

    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
