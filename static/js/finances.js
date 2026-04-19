async function request(url, method="GET", data=null, onload=null, contentType="json", respType="json") {
    try {
        const options = {};
        if (method != "GET") {
            if (contentType == "json") {
                options["headers"] = {"Content-Type":"application/json"};
                options["body"] = JSON.stringify(data);
            } else {
                options["body"] = data;
            }
        }
        const response = await fetch(url, options);

        if (!response.ok) throw new Error('Request failed');

        const result = await response.json();
        if (!data.success) {
            showToast(data.msg, data.msgType, data.msgDur);
        }

        onload(result);
    } catch (error) {
        console.error("Request Error:", error.message);
        showToast(error.message);
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