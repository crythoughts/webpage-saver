(function(){
    const data = {}

    // ^ do not move ^

    console.log(data)
    document.addEventListener('DOMContentLoaded', () => {
        const class_name = String(Date.now());
        document.querySelector('body').insertAdjacentHTML('afterbegin', `
            <style id="s${class_name}">
                #p${class_name} {
                    position: fixed;
                    right: 10px;
                    top: 10px;
                    background: white;
                    border: 6px solid #b0b0b0;
                    box-shadow: 0px 0px 10px 0px rgba(34, 60, 80, 0.3);
                    box-sizing: border-box;
                    padding: 5px;
                    width: 100px;
                    height: 100px;
                    z-index: 9999999;
                }
            </style>
            <div id="p${class_name}">
                <a href="/page/${data.identify}?mode=meta">About</a>
                <a href="javascript:void(0)" onclick="p${class_name}.remove();s${class_name}.remove()">Close</a>
            </div>
        `)
    })
})()
