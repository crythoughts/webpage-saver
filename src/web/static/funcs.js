function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

async function downloadWebdriver() {
    const d = document.querySelector('#download_w')
    const t = confirm('Download latest stable chromedriver?')

    if (t) {
        d.innerHTML = `Downloading...`
        let f = null

        try {
            f = await fetch('/api/webdrivers/download', {'method': 'POST'})
            f = await f.text()
            f = JSON.parse(f)
        } catch(e) {
            alert(String(f))
        }

        location.reload()
    }
}

async function save_ws(url, link_to) {
    document.querySelector('#save').style.display = 'none'
    document.querySelector('#save-win').classList.remove('hidden')

    await save_submit(url, link_to)
}

function stopWebdriver(id) {
    fetch('/api/webdrivers/stop?id=' + id, {method: 'PATCH'})
}

function make_webdriver_default(id) {
    fetch('/api/webdrivers/setDefault?id=' + id, {method: 'PUT'}).then(e => {
        location.reload()
    })
}

function delete_webdriver(id) {
    fetch('/api/webdriver?id=' + id, {method: 'DELETE'}).then(e => {
        location.reload()
    })
}

function save_submit(url, link_to = null) {
    const f = new FormData()
    f.append('url', url)
    if (link_to) {
        f.append('link_to', link_to)
    }

    const res = fetch('/api/pages/save', {
        method: 'POST',
        body: f
    }).then(response  => {
        if (!response.ok) {
            response.text().then(e => {
                alert(e)
                location.reload()
            })
            return
        }

        response.json().then(r => {
            window.location.assign('/page?id=' + r[0].path_to)
        })

    }).catch(err => {
        alert(err.message)
    })
}

function fastSaveByURL(node) {
    const c = new URL(location.origin + '/save')
    c.searchParams.set('preset_url', node.value)
    c.searchParams.set('auto_run', 1)

    location.assign(c.toString());
}

async function edit(page_id, new_taken) {
    const f = await fetch('/api/page?id='+page_id+'&new_taken=' + Number(new_taken), {method: 'PATCH'})
    location.reload()
}

function deletePage(page_id) {
    if (confirm('Delete page with id ' + page_id + '?')) {
        fetch('/api/page?id='+page_id, {method: 'DELETE'}).then(history.back())
    }
}

function openPageInIframe(id) {
    if (document.querySelector('#page-iframe')) {
        return
    }

    document.querySelector('#openPageInIframe').style.display = 'none'
    document.querySelector('#screenshot').style.display = 'none'
    document.querySelector('#screenshot').parentNode.insertAdjacentHTML('beforeend', `
        <iframe id="page-iframe" class="w-full h-full" src="/page?id=${id}"></iframe>
    `)

    const v = document.querySelector('#page-main')
    v.classList.remove('grid')
    v.querySelector('.relative').classList.add('pb-10')
    v.querySelector('iframe').style.minHeight = '80vh'
}

function openPhoto(element, event) {
    element.parentNode.href = event.currentTarget.querySelector('img').dataset.url
    element.src = event.currentTarget.querySelector('img').src
}

function hover_search(event) {
    const url = event.currentTarget.dataset.screenshot
    if (url) {
        document.querySelector('#hover_img').src = url
    }
    document.querySelector('#hover_url').innerHTML = escapeHtml(event.currentTarget.dataset.url)
}
