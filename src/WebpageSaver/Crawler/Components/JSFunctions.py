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

def getLinksClickCatcherScript():
    return ''''''
