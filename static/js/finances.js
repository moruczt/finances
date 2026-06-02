async function request(url, method="GET", data=null, onload=null, contentType="json", respType="json") {
    try {
        const options = {};
        if (method != "GET") {
            options["method"] = method;
            if (contentType == "json") {
                options["headers"] = {"Content-Type":"application/json"};
                options["body"] = JSON.stringify(data);
            } else {
                options["body"] = data;
            }
        }
        const response = await fetch(url, options);
        console.log(response)
        const resp = await response.json();
        console.log(resp)
        if (resp.msg) showToast(resp.msg, resp.msgType, resp.msgDur);

        onload(resp);
    } catch (error) {
        console.error("Request Error:", error.message);
        showToast("Unexpected error");
        onload({"success":false});
        throw error;
    }
}

function showToast(msg, type='error', duration=4000) {
    const container = document.getElementById("toast-container");

    const toast = document.createElement("div");
    toast.className = `toast toast-${type} translate-y-10 opacity-0`;
    toast.textContent = msg;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove("translate-y-10","opacity-0");
    }, 10);

    const removeToast = () => {
        toast.classList.add("opacity-0", "scale-95");
        setTimeout(() => toast.remove(), 300);
    };

    const timeout = setTimeout(removeToast, duration);

    toast.onclick = () => {
        clearTimeout(timeout);
        removeToast();
    }
}


function showConfirm(title, message, confirmText ) {
    return new Promise((resolve) => {
        const modalHtml = `
            <div id="customModalOverlay" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm opacity-0 transition-opacity duration-200">
                <div id="customModalCard" class="w-full max-w-sm bg-white rounded-2xl shadow-xl border border-gray-100 p-6 transform scale-95 opacity-0 transition-all duration-200">
                    <h3 class="text-base font-bold text-gray-900">${title}</h3>
                    <p class="text-xs text-gray-500 mt-2 leading-relaxed">${message}</p>
                    
                    <div class="flex items-center justify-end gap-2 mt-6">
                        <button id="modalCancelBtn" class="px-3.5 py-2 rounded-xl border border-gray-200 text-xs font-semibold text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer">
                            Cancel
                        </button>
                        <button id="modalConfirmBtn" class="px-3.5 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-xs font-semibold text-white shadow-sm transition-colors cursor-pointer">
                            ${confirmText || 'Confirm'}
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const overlay = document.getElementById('customModalOverlay');
        const card = document.getElementById('customModalCard');
        const cancelBtn = document.getElementById('modalCancelBtn');
        const confirmBtn = document.getElementById('modalConfirmBtn');

        const closeModal = (resultValue) => {
            card.classList.add('scale-95', 'opacity-0');
            overlay.classList.add('opacity-0');
            setTimeout(() => {
                overlay.remove();
                resolve(resultValue);
            }, 200);
        };

        requestAnimationFrame(() => {
            overlay.classList.remove('opacity-0');
            card.classList.remove('scale-95', 'opacity-0');
        });

        confirmBtn.addEventListener('click', () => {
            confirmBtn.disabled = true;
            confirmBtn.innerText = "Processing...";
            closeModal(true);
        });

        cancelBtn.addEventListener('click', () => closeModal(false));
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(false); });
    });
}