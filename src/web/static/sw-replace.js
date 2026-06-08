self.addEventListener('fetch', async event => {
    const request = event.request;
    const content_type = request.headers.get("Content-Type");
    let should_proxy_be_applied = true;
    let should_asset_be_proxied = true;
    const u = new URL(request.url);
    const ref = new URL(request.referrer);

    //if (content_type && content_type.startsWith('text/css')) {
    /*if (request.mode == 'style') {
        event.respondWith(
            fetch(event.request).then(async (response) => {
                const text = await response.text();
                const modified = text.replace(/url\((["\']?)\.\.\/([^:)\'"]+)\)/g, 
                                            (match, quote, path) => {
                return `url(${quote}${path.replace(/^\.\.\//g, '')}${quote})`;
                });
                return new Response(modified, {
                    status: response.status,
                    headers: { 'Content-Type': 'text/css' }
                });
            })
        );
    }*/

    // its view page
    maybe = '/page/' + String((new Date()).getFullYear()).substring(0, 1);
    if (ref.pathname.startsWith(maybe) || ref.pathname.startsWith('/page/asset')) {
        if (ref.searchParams.get('mode') == 'page' || ref.searchParams.get('mode') == null) {
            if (!['no-cors', 'cors', 'same-origin'].includes(request.mode)) {
                should_proxy_be_applied = false;
            }
        } else {
            should_proxy_be_applied = false;
        }
    } else {
        should_proxy_be_applied = false;
    }

    if (u.pathname == '/page/asset') {
        if (u.searchParams.get('id') != null) {
            should_asset_be_proxied = false;
        }
    }

    if (request.mode === 'navigate') {
        should_asset_be_proxied = false;
    }

    const should_proxy = should_proxy_be_applied && should_asset_be_proxied;

    //console.log( request, ref.pathname, ref.pathname.startsWith('/page/asset'), ref.searchParams.get('mode'), u.pathname, should_proxy, should_proxy_be_applied, should_asset_be_proxied)

    if (!should_proxy) {
        event.respondWith(
            fetch(request)
        );
        return;
    }

    let v0 = null;
    let nu = null;

    // console.log('Got request:', request)

    event.respondWith(
        (async () => {
            const client = await self.clients.get(event.clientId)
            if (client) {
                v0 = new URL(client.url);
            }
            const v = v0.pathname;
            const v1 = v.split('/');
            const v2 = v1[v1.length - 1]

            nu = new URL(v0.origin + '/page/asset')
            nu.searchParams.set('id', v2);

            if (u.origin == ref.origin) {
                nu.searchParams.set('asset_url', u.pathname);
            } else {
                nu.searchParams.set('asset_url', u.href);
            }
            nu.searchParams.set('content_type', content_type);

            return fetch(String(nu), {
                mode: 'cors',
                credentials: 'omit'
            })
        })()
    )
});
