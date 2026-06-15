### API Endpoints

`GET` **`/api/webdrivers`**

Returns list of all webdrivers from config.

`POST` **`/api/webdrivers/download`**

Downloads latest headless chrome.

`PATCH` **`/api/webdrivers/stop`**

Stops webdriver.

Query params:

`id`: ID of the webdriver. (index in array)

`PUT` **`/api/webdrivers/setDefault`**

Makes webdriver default on every new archivation.

Query params:

`id`: ID of the webdriver. 

`POST` **`/api/pages/save`**

Archives page.

POST params:

`url`: URL to save.

`link_to`: Pages that brought to here (ids)

`webdriver`: ID of the webdriver. If not passed, will take default webdriver's id.

`ignore_no_length`: On `1`: will not download asset to page's dir if `Content-Length` is not passed.

`max_asset_size_mb`: Do not downloads assets if they are bigger than passed values (in MB) (default - 30)

`scroll_down`: on `1`: Scrolls page down. It may be useful for sites, where content is dynamically loaded on the reaching of the end of page.

`scroll_times`: if `scroll_down`=`1`: the maximum times of scrolling down.

`POST` **`/api/pages/html_save`**

Saves page by HTML.

POST params:

`html`: HTML string

`url`: The URL from which the HTML was retrieved

`remove_js`: on `1`: removes `<script>`-tags from passed HTML

`title`: Title of the page (when it exist)

`GET` **`/api/pages`**

Returns pages.

On no query params: returns every page from the `cache.db`

On `id`: Returns only pages with this ids.

On `q`: returns pages by query (url, domain)

`exact_match`: on `1`: searches only this domain, not all subdomains; only this url, not all urls etc.

`display_mode`: `mini`: returns `items` and `count`.
on `calendar`: returns items divided by years, months and days.

`DELETE` **`/api/page`**

Deleted page (by query param `id`).

`PATCH` **`/api/page`**

Changes `taken` of the page (got by query param `id`) to what passed in query param `new_taken`.

### Pages

`GET` **`/page/{id}`**

Renders page, got by query param `id`.

Query params:

`mode`: 

- `page` - default.
- `text` - only text from page
- `page_options` - page with the options
- `meta` - page with info about archived page
- `all_assets` - requests of the page
- `metatags` - page with metatags, scripts and links
- `media` - page with media from the page
- `hyperlinks` - pages with hyperlinks from this page
- `linked` - pages that connected to this page
- `stats` - tag stats.

---

`remove_scripts`: on `on`: removes all `<script>` tags.

`remove_inline_css`: on `on`: removes all `style` attrs.

`remove_styles`: on `on`: removes styles.

`remove_iframes`: on `on`: removes `<iframe>` tags.

`remove_meta`: on `on`: removes metatags.

`remove_selectors`: removes passed selectors

`remove_integrity`: removes `integrity` attrs.

`remove_funcs`: on `on`: removes url moving functions like `window.open`

`catch_clicks`: on `on`: prevents links original purpose and form submitting.

`relay_sw`: on `on`: do not changes assets on the page.

`original_links`: on `on`: do not changes hyperlinks on the page.

`remove_tables`: on `on`: changes `<table>` and related tags on `<div>`

`display_panel`: on `on` (default): displays block with "about" link on the right top corner.

`original_iframes`: on `on`: do not changes iframes.

`original_canvas`: on `on`: do not changes `<canvas>`es.

`encoding`: encoding of the page (default `utf-8`)

`GET` **`/page/screenshot`**

Returns screenshot of page or the canvas from page.

Query params:

`id`: ID of the page.

`file`: Filename of the screenshot. Fullscreen - `fullscreen.jpeg`, viewport - `viewport.jpeg`, canvas - `canvas_{id}.jpeg`

`GET` **`/page/asset`**

Returns asset from the page.

Query params:

`id`: ID of the page.

`asset_url`: Original URL of the asset.

or

`path`: ID of the asset.

There is other path:

`/page/asset/{identify}/{path:}`: returns asset by path. Useful if there is relative URLs in file (styles) and route matter.

`GET` **`/api/page/metatags`**

Same as `mode`=`meta`, but in json. Page id should be passed in query param `id`.

`GET` **`/api/page/requests`**

Same as `mode`=`all_assets`. Page id should be passed in query param `id`.

`show_from_html`: on `1`: takes assets from html instead of requests.

`GET` **`/api/page/media`**

Same as `mode`=`media`. Page id should be passed in query param `id`.

`GET` **`/api/page/hyperlinks`**

Same as `mode`=`hyperlinks`. Page id should be passed in query param `id`.

`GET` **`/api/page/stats`**

Same as `mode`=`stats`. Page id should be passed in query param `id`.

`GET` **`/api/page/linked`**

Same as `mode`=`linked`. Page id should be passed in query param `id`.

`every_pages`: on `1`: returns all linked pages from all pages with url of selected page
