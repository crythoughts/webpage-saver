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

const save_list = new class {
    constructor() {
        this.list = []
        this.id = 0
        this.selected = null
    }

    getId() {
        const id = Number(this.id)
        this.id += 1
        return id
    }

    addUrl(url) {
        const id = this.getId()

        this.selected = id
        const tpl = `
        <a data-id="${id}" href="javascript:void(0)" class="download-item box-border truncate bg-slate-300 py-1 px-2 h-8 grid grid-cols-[0fr_1fr] items-center gap-2">
            <div class="ico w-4 h-4 bg-slate-100"></div>
            <span>Loading... ${escapeHtml(url)}</span>
        </a>
        `
        itms.insertAdjacentHTML('beforeend', tpl)

        return id
    }

}()

async function save_ws(url, link_to) {
    if (url == null || url.length == 0) {
        return
    }

    const fd = new FormData(main_save_form)

    document.querySelector('#url').value = ''
    //document.querySelector('#save-win').classList.remove('hidden')

    const id = save_list.addUrl(url)
    fetch('/api/pages/save', {
        method: 'POST',
        body: fd
    }).then(response  => {
        if (!response.ok) {
            response.text().then(e => {
                alert(e)
            })
            return
        }

        response.json().then(r => {
            const n = document.querySelector(`.download-item[data-id='${id}']`)
            console.log(n, r)

            n.classList.remove('bg-slate-300')
            n.classList.add('bg-green-300')
            n.href = '/page/' + r[0].path_to + '?mode=meta'
            n.querySelector('span').innerHTML = escapeHtml(r[0].title)
            if (save_list.id == 1 && document.querySelector('#url').value == '') {
                window.location.assign('/page/' + r[0].path_to + '?mode=meta')
            }
            n.querySelector('.ico').insertAdjacentHTML('beforeend', `
                <img src="${r[0].favicons[0].url}">    
            `)

        })

    }).catch(err => {
        alert(err.message)
    })
}
