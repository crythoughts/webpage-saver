
from WebpageSaver.Crawler.WebPage import WebPage
from WebpageSaver.Crawler.Assets.Asset import Asset
from WebpageSaver.Crawler.Assets.Meta import Meta
from WebpageSaver.Crawler.Assets.Favicon import Favicon
from WebpageSaver.Crawler.Assets.Media import Media
from WebpageSaver.Crawler.Assets.Link import Link
from WebpageSaver.Crawler.Assets.URL import URL
from WebpageSaver.Crawler.Assets.Script import Script
from WebpageSaver.Crawler.Components.JSFunctions import getNavRemoveScript, getLinksClickCatcherScript
from bs4.dammit import EncodingDetector
from bs4 import BeautifulSoup
from collections import Counter
from typing import Generator
from WebpageSaver import config
from yarl import URL as UURL
import re
import json
import logging
import brotli

class PageHTML:
    bs: BeautifulSoup = None
    encoding: str

    def get_favicons(self, orig_page: WebPage, take_default: bool = False) -> Generator:
        for icon in self.bs.select("link[rel*='icon']"):
            favicon = Favicon(sizes = getattr(icon, 'sizes', None))
            favicon.set_url(orig_page.getRelativeURL(icon.get('href')))
            favicon.set_node(icon)

            yield favicon

        if take_default:
            yield Favicon(url = orig_page.base_url + '/favicon.ico')

    def get_media(self, orig_page: WebPage, selector: str = None, original_urls: bool = True, set_local_urls: bool = False, show_from_requests: bool = False) -> Generator:
        if selector == None:
            selector = "[src]:not(iframe)"

        if show_from_requests:
            for item in orig_page.getMediaFromRequests(set_local_urls = set_local_urls, selector = selector):
                yield item

            return

        for tag in self.bs.select(selector):
            item = Media()
            item.tagName = tag.name

            src = ''

            if original_urls:
                src = tag.get(orig_page.getOrigAttr())
            if set_local_urls:
                item.set_local_url(tag.get('src'))
            if src == None or original_urls == False:
                src = tag.get('src')

            item.set_url(orig_page.getRelativeURL(src))
            item.set_node(tag)
            if tag.get('alt'):
                item.alt = tag.get('alt')

            yield item

    def get_meta(self, orig_page: WebPage) -> Generator:
        for tag in self.bs.select("meta"):
            meta = Meta()
            meta.set_node(tag)

            for key, attr in tag.attrs.items():
                if key == 'class':
                    continue

                setattr(meta, key, attr)

            yield meta

    def get_links(self, orig_page: WebPage):
        for tag in self.bs.select("link"):
            item = Link()
            item.set_node(tag)

            url = tag.get('href')
            if len(tag.get('href', '')) == 0:
                url = tag.get(orig_page.getOrigAttr())
            item.set_url(orig_page.getRelativeURL(url))

            for key, attr in tag.attrs.items():
                try:
                    if key != 'href':
                        setattr(item, key, attr)
                except Exception as e:
                    logging.exception(e)

            yield item

    def get_downloadable_links(self, orig_page: WebPage):
        for item in self.get_links(orig_page):
            #print(item.url, item.should_download())
            if item.should_download() == False:
                continue

            yield item

    def get_urls(self, orig_page: WebPage, keep_original_urls: bool = True, only_with_href: bool = True):
        s = 'a'
        if only_with_href:
            s = 'a[href]'

        for tag in self.bs.select(s):
            label = tag.text

            url = URL()
            url.set_node(tag)
            if type(label) == str:
                url.label = label

            for key, attr in tag.attrs.items():
                try:
                    if key == 'target':
                        url.target = attr
                    elif key == 'href':
                        is_protocol = False
                        _parts = attr.split(':')
                        if len(_parts) > 2:
                            is_protocol = _parts[1] != '/'

                        if attr[0] == '#':
                            logging.info('url {0}: anchor'.format(attr))
                        elif attr[0] == '' or attr == None:
                            logging.info('url {0}: empty url'.format(attr))
                        elif is_protocol:
                            logging.info('url {0}: probaly protocol'.format(attr))
                            url.set_protocol(attr)
                        else:
                            if keep_original_urls:
                                url.set_url(orig_page.getRelativeURL(attr))
                            else:
                                url.set_url(attr)
                    elif key == 'download':
                        url.is_download = True
                    else:
                        setattr(url, key, attr)
                except Exception as e:
                    logging.exception(e)
                    continue

            yield url

    def get_scripts(self, orig_page: WebPage):
        for tag in self.bs.select("script"):
            item = Script()
            item.set_node(tag)

            src = tag.get('src')
            if src == None or len(src) == 0:
                src = tag.get(orig_page.getOrigAttr())

            try:
                    item.set_url(orig_page.getRelativeURL(src))
            except:
                pass

            #else:
            #    pass
                #for key, attr in tag.attrs.items():
                    #if key in ['rel', 'href']:
                    #    continue

                #    setattr(item, key, attr)

            yield item

    def move_head(self) -> str:
        head_html = ''
        for tag in ['title', 'meta', 'base', 'link']:
            for item in self.bs.select(tag):
                head_html += str(item)

                item.decompose()

        return head_html

    def remove_iframes(self):
        for tag in self.bs.select('iframe'):
            tag.decompose()

    def remove_meta(self):
        for tag in self.bs.select('meta'):
            tag.decompose()

    def remove_selectors(self, selectors: list | str):
        if type(selectors) != list:
            selectors = [selectors]

        for selector in selectors:
            for tag in self.bs.select(selector):
                tag.decompose()

    def clear_js(self, softly: bool = False):
        logging.info('removing all js functions from tags and script tags')

        for tag in self.bs.select('script'):
            if softly:
                tag.name = 'scriptd'
                tag['style'] = 'display:none;'
            else:
                tag.decompose()

        for tag in self.bs.select('noscript'):
            if softly:
                tag.name = 'noscriptd'
                tag['style'] = 'display:none;'
            else:
                tag.decompose()

        for tag in self.bs.select('*'):
            attrs_to_remove = []
            for attr in tag.attrs:
                if re.match(r'^on\w+', attr, re.IGNORECASE):
                    attrs_to_remove.append(attr)
                elif isinstance(tag[attr], str) and 'javascript:' in tag[attr].lower():
                    attrs_to_remove.append(attr)

            for attr in ['href', 'src', 'action']:
                if tag.has_attr(attr) and tag[attr] and 'javascript:' in str(tag[attr]).lower():
                    attrs_to_remove.append(tag[attr])

            tag.attrs = {key:value for key,value in tag.attrs.items()
                    if key not in attrs_to_remove}

    def add_nav_remove_script(self):
        s = self.bs.new_tag('script')
        s.string = getNavRemoveScript()

        self.bs.find('head').insert(0, s)

    def add_catch_events(self, page: WebPage):
        s = self.bs.new_tag('script')
        s.string = getLinksClickCatcherScript(page)

        self.bs.find('head').insert(0, s)

    def add_display_panel_script(self, page: WebPage):
        s = self.bs.new_tag('script')
        data = json.dumps(page.dump(), ensure_ascii = False)
        scr = config.cwd.joinpath('web').joinpath('static').joinpath('page-panel.js')
        scr_text = scr.read_text()
        scr_text = scr_text[:30] + data + scr_text[32:]
        s.string = scr_text

        self.bs.find('head').insert(0, s)

    def remove_inline_css(self):
        for tag in self.bs.find_all(attrs={"style": True}):
            del tag['style']

    def remove_html_stylization(self):
        for i in ['background', 'bgcolor', 'color']:
            for tag in self.bs.find_all(attrs={i: True}):
                del tag[i]

    def remove_css(self):
        for tag in self.bs.select('style'):
            tag.decompose()

        for tag in self.bs.select('link[rel=\'stylesheet\']'):
            tag.decompose()

    def remove_integrity(self):
        for tag in self.bs.find_all(attrs={"integrity": True}):
            del tag['integrity']

    def make_local_links_to_assets(self, page: WebPage, remove_temporary_attrs: bool = True):
        #for item in self.bs.select('link[href]'):
        #    if item.get(page.getOrigAttr()) != None:
        #        continue

        #    _href = item.get('href')
        #    if _href:
        #        item['href'] = '{0}{1}'.format(page.relative_url, _href)

        # replacing assets
        for item in self.bs.select('[' + page.getOrigAttr() + ']:not(canvas)'):
            #_url = base64.urlsafe_b64encode(('assets/' + _file_url).encode()).decode()
            _url = item[page.getOrigAttr()]
            _key = item[page.getKeyAttr()]
            _id = page.getAssetByUrl(_url)

            # removing internal data attributes
            if _id == None:
                item['data-__err'] = 'missing'
                #item[_key] = '#'
                #logging.error('page {0}: element \"{1}\" is missing'.format(page.identify, _url))

                continue

            if remove_temporary_attrs:
                item.attrs = {key:value for key,value in item.attrs.items()
                        if key not in [page.getOrigAttr(), page.getKeyAttr()]}

            #item[_key] = _id[1].asset.getLocalURL(page, _id[0])
            item[_key] = _id[1].asset.getLocalURL(page, id = _id[0], path = _url)

    def make_links_local(self, page: WebPage):
        for item in self.bs.select('meta[http-equiv]'):
            item.decompose()

        # Replacing hrefs
        for item in self.bs.select('a[href]'):
            _href = item.get('href')
            if _href:
                if URL.isAURL(_href) == False:
                    continue

                potential_page = page.findLinkedPageByUrl(_href)

                if potential_page:
                    item['href'] = '/page/' + potential_page.identify
                else:
                    item['href'] = '/page/{0}?mode=url&url={1}'.format(page.identify, Asset.encodeURL(_href))

    def make_iframes_local(self, page: WebPage):
        pages = list(page.getIframes())

        for frame in self.bs.select('iframe'):
            _href = frame.get('src')
            need = None

            try:
                u = UURL(page.getRelativeURL(_href))
                
                for page in pages:
                    if UURL(page.url) == u:
                        need = page
                        break

                if need:
                    frame['src'] = '/page/' + need.identify + '?display_panel=off'
            except Exception as e:
                logging.exception(e)

    def make_canvases_local(self, page: WebPage):
        for item in self.bs.select('canvas[{0}]'.format(page.getOrigAttr())):
            try:
                item.name = 'div'
                attr = item.get(page.getOrigAttr())
                u = page.canvases[attr]

                item.clear()
                new_html = BeautifulSoup(u.toHTML(page))
                item.append(new_html)

                item['src'] = ''
            except Exception as e:
                logging.exception(e)

    def prettify(self, encoding: str = 'utf-8') -> str:
        if encoding == 'br':
            return str(self.bs).encode(encoding = 'utf-8')

        return str(self.bs).encode(encoding = encoding)

    def clear(self, page, clear_js: bool = False,
            remove_integrity: bool = False,
            remove_inline_css: bool = False,
            remove_styles: bool = False,
            remove_iframes: bool = False,
            remove_meta: bool = False,
            remove_funcs: bool = False,
            catch_clicks: bool = False,
            relay_sw: bool = False,
            original_links: bool = False
              ):
        if clear_js:
            self.clear_js()

        if remove_integrity:
            self.remove_integrity()
        if remove_inline_css:
            self.remove_inline_css()
            self.remove_html_stylization()
        if remove_styles:
            self.remove_css()
        if remove_iframes:
            self.remove_iframes()
        if remove_meta:
            self.remove_meta()
        if remove_funcs:
            self.add_nav_remove_script()
        if catch_clicks:
            self.add_catch_events(page)

    @classmethod
    def from_html(cls, html: str):
        _src = cls()

        _src.encoding = EncodingDetector.find_declared_encoding(html, is_html=True)

        logging.info('detected encoding {0}'.format(_src.encoding))

        _src.bs = BeautifulSoup(html, 'html.parser')

        return _src

    def _getStats(self) -> dict[str, int]:
        tag_counter = Counter(tag.name for tag in self.bs.find_all())

        return dict(tag_counter.most_common())

    def getStats(self):
        tag_counter = Counter()
        attr_counters = {} 

        for tag in self.bs.find_all():
            tag_name = tag.name
            tag_counter[tag_name] += 1

            if tag_name not in attr_counters:
                attr_counters[tag_name] = Counter()
            
            if tag.attrs:
                attr_counters[tag_name].update(tag.attrs.keys())
        
        result = {}
        for tag, count in tag_counter.most_common():
            if tag in attr_counters and attr_counters[tag]:
                result[tag] = {
                    'count': count,
                    'attributes': dict(attr_counters[tag].most_common())
                }
            else:
                result[tag] = {
                    'count': count,
                    'attributes': dict()
                }
        
        return result
