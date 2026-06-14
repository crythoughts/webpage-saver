from WebpageSaver.API import API
from WebpageSaver.Crawler.Assets.Asset import Asset
from WebpageSaver import config
from WebpageSaver.Crawler.Components.PageHTML import PageHTML
from WebpageSaver.Display.AssetDisplayer import asset_displayer
from WebpageSaver.Crawler.Components.JSFunctions import getSW
from WebpageSaver.Crawler.Components.Utils import getCalendarForPages
import urllib.parse

from yarl import URL
from pathlib import Path
from datetime import datetime
import asyncio
import logging
import aiohttp_jinja2
from aiohttp import web
import jinja2
import urllib
import traceback

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
    return aiohttp_jinja2.render_template('@index.html',request,{
        'sw_js': getSW()
    })

@routes.get('/settings')
@routes.post('/settings')
async def settings(request: web.Request):
    if request.method == 'POST':
        data = await request.post()

        config.set('navigation_save', int(data.get('a') == 'on'))
        config.set('navigation_first_found', int(data.get('b') == 'on'))

    return aiohttp_jinja2.render_template('@settings.html', request, {
        'config': config
    })

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

    pages = api.getPagesById(ids = [page_id], convert = False)
    if len(pages) == 0:
        return web.Response(status = 404)

    page = pages[0]
    # Encoding
    errors_descriptions = {
        'encoding': 'Decoding error occured. Try to choose another encoding (or choose utf-8).'
    }
    encoding = page.encoding
    if query.get('encoding') != None:
        encoding = query.get('encoding')

    match (mode):
        case 'page_options':

            error = query.get('error')

            return aiohttp_jinja2.render_template('page_options.html', request, {
                'page': page,
                'id': page_id,
                'back_btn': '/page/' + page_id + '?mode=meta',
                'error': errors_descriptions.get(error),
            })

        case 'meta':

            return aiohttp_jinja2.render_template('page_info.html', request, {
                'page': page,
                'taken': page.getReadableTaken(),
                'linked_count': len(page.linked_pages),
            })

        case 'url':

            p_url = query.get('url')
            new_url = Asset.getDecodedURL(p_url)
            redirect_url = page.getRelativeURL(new_url)

            candidates_to_redirect = api.getPagesByURL(redirect_url, page.taken, conv = False)

            if config.get('navigation_first_found', 1) == 1 and len(candidates_to_redirect) > 0:
                logging.info('navigation_first_found=1, ref {0}, url {1}, redir to {2}'.format(page_id, new_url, candidates_to_redirect[0].identify))

                u = URL(request.url).with_name(candidates_to_redirect[0].identify)

                return web.HTTPFound(location = str(u))

            do_nav_save = True
            # Automatically saving page
            if config.get('navigation_save') == 1:
                if len(candidates_to_redirect) > 0:
                    if config.get('navigation_save_ignore_found', 0) == 1:
                        logging.info('found {0} candidates to redirect, but we will ignore them'.format(len(candidates_to_redirect)))
                    else:
                        do_nav_save = False

                if do_nav_save:
                    logging.info('navigation_save=1, ref {0}, url {1}'.format(page_id, new_url))

                    payload = None
                    try:
                        payload = await api.savePage(url = redirect_url, link_pages = [page], conv = False)
                    except Exception as e:
                        raise web.HTTPBadRequest(str(e))

                    u = URL(request.url).with_name(payload[0].identify)
                    return web.HTTPFound(location = str(u))

            return aiohttp_jinja2.render_template('url.html', request, {
                'url': redirect_url,
                'id': page.identify,
                'back_btn': '/page/' + page_id,
                'possible_pages': candidates_to_redirect,
                'possible_pages_count': len(candidates_to_redirect)
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
                'str': str,
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'media':

            show_from_html = query.get('show_from_html') == 'on'
            mmode = query.get('mmode')
            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)
            if query.get('original') != 'on':
                html.make_local_links_to_assets(page, remove_temporary_attrs = False)

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

            medias = html.get_media(page, selectors, set_local_urls = True, show_from_requests = show_from_html == False)

            return aiohttp_jinja2.render_template('media.html', request, {
                'media': medias,
                'mmode': mmode,
                'mmodes': {'': 'Type', 'all': 'All', 'img': 'Images', 'video': 'Videos'},
                'back_btn': '/page/' + page_id + '?mode=meta',
                'show_from_html': query.get('show_from_html')
            })

        case 'hyperlinks':

            rel = query.get('rel', 'off')

            text = page.getRootFile().read_text(encoding = encoding)
            html = PageHTML.from_html(text)
            if rel == 'on':
                html.make_local_links_to_assets(page)

            return aiohttp_jinja2.render_template('hyperlinks.html', request, {
                'urls': html.get_urls(page, keep_original_urls = rel == 'off'),
                'page': page,
                'list': list,
                'back_btn': '/page/' + page_id + '?mode=meta'
            })

        case 'linked':

            every_pages = query.get('every') == 'on'
            pages = list(page.linked_pages)

            return aiohttp_jinja2.render_template('linked_pages.html', request, {
                'page': page,
                'back_btn': '/page/' + page_id + '?mode=meta',
                'linked': page.getLinkedPages(every_pages = every_pages),
                'count': len(pages),
                'every_pages': every_pages
            })

        case 'stats':

            try:
                text = page.getIndexPageText(encoding)
            except UnicodeDecodeError as e:
                logging.exception(e)
                return web.HTTPFound(location = '/page/{0}?mode=page_options&error=encoding'.format(page.identify))

            html = PageHTML.from_html(text)

            return aiohttp_jinja2.render_template('stats.html', request, {
                'back_btn': '/page/' + page_id + '?mode=meta',
                'stats': html.getStats(),
            })

        # Page display
        case _:

            if mode == 'text':
                query['remove_scripts'] = 'on'
                query['remove_inline_css'] = 'on'
                query['remove_styles'] = 'on'
                query['remove_iframes'] = 'on'
                query['remove_meta'] = 'on'
                query['remove_selectors'] = 'nav, header, input, button'

            if page.redirected_to != None:
                redir = page.getRedirection()
                return aiohttp_jinja2.render_template('redirect.html', request, {
                    'page': page,
                    'back_btn': '/page/' + page_id + '?mode=meta',
                    'redir': redir
                })

            try:
                text = page.getIndexPageText(encoding)
            except UnicodeDecodeError as e:
                logging.exception(e)
                return web.HTTPFound(location = '/page/{0}?mode=page_options&error=encoding'.format(page.identify))

            html = PageHTML.from_html(text)

            html.clear(page,
                clear_js = query.get('remove_scripts', config.get('remove_scripts_by_default', True)) == 'on',
                remove_integrity = query.get('remove_integrity') == 'on',
                remove_inline_css = query.get('remove_inline_css') == 'on',
                remove_styles = query.get('remove_styles') == 'on',
                remove_iframes = query.get('remove_iframes') == 'on',
                remove_meta = query.get('remove_meta') == 'on',
                remove_funcs = query.get('remove_funcs', 'on') == 'on',
                catch_clicks = query.get('catch_clicks', 'on') == 'on',
                relay_sw = query.get('relay_sw') != 'on',
                original_links = query.get('original_links') != 'on'
            )

            try:
                if query.get('remove_selectors') != None:
                    html.remove_selectors(query.get('remove_selectors'))
            except:
                pass

            if query.get('display_panel', 'on') == 'on':
                html.add_display_panel_script(page)

            if query.get('relay_sw') != 'on':
                html.make_local_links_to_assets(page)

            if query.get('original_links') != 'on':
                html.make_links_local(page)

            if query.get('original_iframes') != 'on':
                html.make_iframes_local(page)

            if query.get('original_canvas') != 'on':
                html.make_canvases_local(page)

            #head_html = html.move_head()

            return web.Response(
                body = html.prettify(encoding = encoding), 
                content_type='text/html',
                charset = encoding
            )

@routes.get('/page/asset')
@routes.get('/page/asset/{identify}/{path:.*}')
async def gpa(request: web.Request):
    query = request.rel_url.query

    #asset_url = query.get('asset_url', None)
    asset_url = request.match_info.get('path', None)
    page_id = query.get('id')

    if asset_url != None:
        query_string = URL(request.url).query_string or ''

        if len(query_string) > 0:
            asset_url = asset_url + '?' + query_string

        page_id = int(request.match_info.get('identify'))

    path_id = query.get('path', '')

    pages = api.getPagesById(ids = [page_id], convert = False)
    if len(pages) == 0:
        return web.HTTPNotFound(body = 'Not found page')

    page = pages[0]
    req = None

    if asset_url != None:
        param_name = 'internal_content_type_param_and_i_hope_noone_will_use_this_in_real_cases'
        asset_url = URL(urllib.parse.unquote(asset_url))
        query_dict = dict(asset_url.query)
        query_dict.pop(param_name, None)

        _ = page.getAssetByUrl(str(asset_url.with_query(query_dict)), query.get(param_name))

        # Not found 
        if _ == None:
            return asset_displayer.getResponseByContentType(query.get(param_name, 'image/jpeg'))

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
    exact_match = query.get('exact_match') == 'on'
    display_mode = query.get('display_mode')

    res = api.findPagesByURL(url = q, conv = False, conv_models = False, exact_match = exact_match)
    search_type = res.get('type')
    ctx = {}

    if display_mode == None:
        match(search_type):
            case 'keywords_search':
                display_mode = 'mini'
                ctx['items'] = res.get('items')
            case 'empty_search':
                display_mode = 'mini'
                ctx['items'] = res.get('items')
            case 'domain_search':
                display_mode = 'calendar'
            case 'urls':
                display_mode = 'calendar'
            case 'accurate_url':
                display_mode = 'calendar'

    if display_mode == 'calendar':
        c = getCalendarForPages(res.get('items'))
        selected_year = int(query.get('year', datetime.now().year))
        selected_month = query.get('month')
        selected_day = query.get('day')

        length = len(res.get('items'))
        ctx['items'] = c
        ctx['count'] = length
        ctx.update({
            'year': selected_year
        })

        try:
            if selected_month != None and selected_day != None:
                day = c.get('years').get(selected_year).get('months').get(int(selected_month)).get('days').get(int(selected_day))
                display_mode = 'mini'
                ctx.update({
                    'selected_day': day,
                    'items': day.get('records'),
                    'back_btn': '/page/search?q=' + q +'&display_mode=calendar&year=' + str(selected_year)
                })
            if selected_month != None and selected_day == None:
                items = list()
                month = c.get('years').get(selected_year).get('months').get(int(selected_month))
                for day in month.get('days').values():
                    for item in day.get('records'):
                        items.append(item)

                display_mode = 'mini'
                ctx.update({
                    'selected_month': month,
                    'items': items,
                    'back_btn': '/page/search?q=' + q +'&display_mode=calendar&year=' + str(selected_year)
                })

        except Exception as e:
            logging.exception(e)

    else:
        ctx['items'] = list()
        for item in res.get('items'):
            ctx.get('items').append(item.toModel())

        ctx['count'] = len(ctx.get('items'))

    ctx.update({
        'q': q,
        'search_type': search_type,
        'exact_match': exact_match,
        'url': res.get('url'),
        'current_url': URL(request.url),
        'quote': urllib.parse.quote,
        'display_mode': display_mode
    })

    ctx['count'] = len(ctx.get('items'))

    if search_type in ['accurate_url', 'domain_search']:
        ctx['append_to_header'] = True

    return aiohttp_jinja2.render_template('search.html', request, ctx)

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
        logging.exception(e)
        raise web.HTTPBadRequest(body = str(e))

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
            #'Cache-Control': 'no-cache',
        }
    )

async def main():
    host = config.get('server.host', '127.0.0.1')
    port = config.get('server.host', 7514)
    client_max_size_megabytes = config.get('server.client_max_size_megabytes', 50)

    app = web.Application(client_max_size = 1024 * 1024 * client_max_size_megabytes)
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
