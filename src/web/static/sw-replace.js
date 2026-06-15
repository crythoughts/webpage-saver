self.addEventListener('fetch', async event => {
    const request = event.request;
    const content_type = request.headers.get("Content-Type");
    let should_proxy_be_applied = true;
    let should_asset_be_proxied = true;
    const clientId = event.clientId;

    event.respondWith(
        (async () => {
            const u = new URL(request.url);
            let v0 = null;
            let nu = null;
            let ref = null;

            const client = await self.clients.get(clientId)
            if (client) {
                v0 = new URL(client.url);
                ref = v0
            } else {
                console.log('no client found!')

                if (request.referrer != null && request.referrer.length > 0) {
                    ref = new URL(request.referrer);
                }
            }
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
            const maybe = '/page/' + String((new Date()).getFullYear()).substring(0, 1);
            if (u.pathname.startsWith('/page/screenshot')) {
                should_proxy_be_applied = false;
            }

            if (ref) {
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
            } else {
                should_asset_be_proxied = false;
            }

            if (u.pathname.startsWith('/page/asset')) {
                //if (u.searchParams.get('id') != null) {
                    should_asset_be_proxied = false;
                //}
            }

            if (request.mode === 'navigate') {
                should_asset_be_proxied = false;
            }

            if (request.referrer == null) {
                should_asset_be_proxied = false;
            }

            const should_proxy = should_proxy_be_applied && should_asset_be_proxied;

            // console.log( request, ref.pathname, u, u.pathname.startsWith('/page/asset'), ref.searchParams.get('mode'), u.pathname, should_proxy, should_proxy_be_applied, should_asset_be_proxied)

            if (!should_proxy) {
                const f = await fetch(request)
                // console.log(f, request.url)
                return f;
            }

            // console.log('Got request:', request)

            const page_ids = v0.pathname.split('/');
            const page_id = page_ids[page_ids.length - 1];

            const v = v0.pathname;
            const v1 = v.split('/');
            const v2 = v1[v1.length - 1]

            nu = new URL(v0.origin + '/page/asset')
            //console.log(u.origin, ref.origin)
            if (u.origin == ref.origin) {
                //console.log(page_id, u.pathname)
                nu = new URL(v0.origin + '/page/asset/' + page_id)
                nu.pathname += u.pathname + (u.search ?? '')
                //nu.searchParams.set('asset_url', u.pathname);
            } else {
                nu.searchParams.set('id', v2);
                nu.searchParams.set('asset_url', u.href);
            }
            nu.searchParams.set('internal_content_type_param_and_i_hope_noone_will_use_this_in_real_cases', content_type);

            return fetch(String(nu), {
                mode: 'cors',
                credentials: 'omit'
            })
        })()
    )
});
