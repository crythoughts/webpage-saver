document.getElementById('sendButton').addEventListener('click', async () => {
    const app_host = document.querySelector('#host').value;
    const remove_js = document.querySelector('#remove_js').checked;
    const only_by_url = document.querySelector('#just_url').checked;
    const button = document.getElementById('sendButton');
    const statusDiv = document.getElementById('status');

    button.disabled = true;
    statusDiv.className = 'loading';
    statusDiv.textContent = 'Sending...';

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        const [{ result: html }] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
                func: () => {
                    try {
                        return (()=>{
                            const extractShadowContent = (element) => {
                                let result = element.outerHTML;
                                
                                if (element.shadowRoot) {
                                    const shadowHtml = Array.from(element.shadowRoot.children)
                                        .map(child => extractShadowContent(child))
                                        .join('');
                                    result = result.replace('>', '><shadow-root>' + shadowHtml + '</shadow-root>');
                                }
                                
                                Array.from(element.children).forEach(child => {
                                    const childHtml = extractShadowContent(child);
                                    result = result.replace(child.outerHTML, childHtml);
                                });
                                
                                return result;
                            };
                            
                            return extractShadowContent(document.documentElement);
                        })()
                    } catch(e) {
                        return document.documentElement.outerHTML
                    }
                }
        });
        const fd = new FormData();
        fd.append('url', tab.url)
        fd.append('remove_js', remove_js ? '1' : '0')
        //document.body.textContent = html;

        let response = null;

        if (only_by_url == true) {
            response = await fetch('http://' + app_host + '/api/pages/save', {
                method: 'POST',
                body: fd,
            });
        } else {
            fd.append('html', html);
            fd.append('title', tab.title);

            response = await fetch('http://' + app_host + '/api/pages/html_save', {
                method: 'POST',
                body: fd,
            });
        }

        if (response.ok) {
            statusDiv.className = 'success';
            statusDiv.textContent = 'Saved!';
            const json = await response.json();

            chrome.tabs.create({ 
                url: 'http://' + app_host + '/page/' + json[0].identify + '?mode=meta',
                active: true,
            });
        } else {
            throw new Error(`HTTP Error: ${response}`);
        }
    } catch (error) {
        statusDiv.className = 'error';
        statusDiv.textContent = String(error);
    } finally {
        setTimeout(() => {
            button.disabled = false;
            if (statusDiv.className === 'success') {
                statusDiv.style.display = 'none';
            }
        }, 2000);
    }
});
