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

async function edit(page_id, new_taken) {
    const f = await fetch('/api/page?id='+page_id+'&new_taken=' + Number(new_taken), {method: 'PATCH'})
    location.reload()
}

function deletePage(page_id) {
    if (confirm('Delete page with id ' + page_id + '?')) {
        fetch('/api/page?id='+page_id, {method: 'DELETE'}).then(history.back())
    }
}

function editPage(page_id, event) {
    event.target.parentNode.insertAdjacentHTML('beforeend', `
        <div>
            <b>New date</b>
            <input type="text" value="${event.target.dataset.taken}" class="p-2 bg-white" id="page_new_date">
        </div>
        <input type="button" class="bg-white" id="save_btn" value="Save">
    `)
    event.target.remove()
    document.querySelector('#save_btn').addEventListener('click', (e) => {
        const date = page_new_date.value;
        fetch('/api/page?id='+page_id + '&new_taken=' + date, {method: 'PATCH'}).then(location.reload())
    })
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
    const id = event.currentTarget.dataset.id
    if (url) {
        document.querySelector('#hover_img').src = url + '&file=viewport.jpeg'
    }
    document.querySelector('#page_id').setAttribute('href', '/page/' + id)
    document.querySelector('#hover_url').innerHTML = escapeHtml(event.currentTarget.dataset.url)
}
