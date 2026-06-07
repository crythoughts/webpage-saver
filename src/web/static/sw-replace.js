self.addEventListener('fetch', async event => {
    const request = event.request;

    //console.log(event.request.referrer)
    if (request.mode === 'navigate') {
        return;
    }

    if (request.url.includes('sw.js')) {
        return;
    }

    if (request.url.includes(location.origin) || request.url.includes('https://cdn.jsdelivr.net/npm/')) {
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
            nu.searchParams.set('asset_url', request.url);
            nu.searchParams.set('content_type', request.headers.get("Content-Type"));

            return fetch(String(nu), {
                mode: 'cors',
                credentials: 'omit'
            })
        })()
    )
});
