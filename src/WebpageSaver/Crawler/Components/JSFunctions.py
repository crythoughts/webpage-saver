def getSW():
    return '''
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            }).then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        }
    '''

def getRedirectBlocker():
    return '''() => {open = null; location.replace = null; history = null; location.reload = null; location.assign = null;}'''

def getXHRBlocker():
    return '''() => {xhr = null; fetch = null;}'''

def getNavRemoveScript():
    return '''
    window.open = (url) => {console.log('tried to open ' + url)};
    location.replace = () => { };
    history.pushState = () => { };
    history.replaceState = () => { };
    location.reload = () => { console.log('tried to reload') };
    location.assign = (url) => { console.log('tried to go to url ' + url) };
    '''

def getLinksClickCatcherScript(page):
    return '''
    (function() {
        document.addEventListener("click", (e) => {
            //e.preventDefault();
            //e.stopImmediatePropagation();

            const t = e.target;

            if (t.tagName == 'A') {
                if (t.href && t.href.startsWith(location.origin) == false) {
                    e.preventDefault();

                    const u = new URL(location.pathname);
                    u.searchParams.set("mode", "url");
                    u.searchParams.set("url", t.href);
                    location.href = String(u);
                };
            };
        });
        document.addEventListener("submit", (e) => {
            e.preventDefault();

            console.log("Form submit: ", e);

            const url = "'''+page.url+'''";
            const t = e.target;
            const f = new FormData(t);
            const g = new URLSearchParams(f).toString();
            const method = t.method;
            let action = t.getAttribute("action");

            if (action && (method == "get" || method == "GET")) {
                if (!action.includes(location.origin)) {
                    let u = new URL(url);
                    u.pathname = action;
                    u.search = g.toString(); 

                    action = u.toString();
                }

                if (confirm("Submit form " + action + " ?")) {
                    location.href = "/page/'''+page.identify+'''?mode=url&url=" + action;
                }
            } else {
                e.preventDefault();
            }
        });
    })()
    '''
