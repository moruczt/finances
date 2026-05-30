async function rawImport(e) {const allowedExtensions = /(\.csv|\.xlsx)$/i;
    const file = e.target.files[0];
    if (!allowedExtensions.exec(file.name)) {
        showToast("Invalid file type! Please upload CSV or Excel.");
        return;
    }

    e.target.disabled = true;
    document.getElementById("spinner").classList.remove("hidden");

    const accountId = document.getElementById("accountSelect").value;
    if (!file) {
        showToast("No file was uploaded", "info");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const onLoad = (resp) => {
        if (resp.success) {
            document.getElementById("importLog").innerHTML = resp.result["import_log"];
        }
        e.target.disabled = false;
        document.getElementById("spinner").classList.add("hidden");
    }

    request(`/finances/api/accounts/${accountId}/import`,"POST", formData, onLoad, "formData")
    e.target.value = "";
}


const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
fileInput.addEventListener("change", rawImport);

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, e => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('border-blue-500!', 'bg-blue-50!');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('border-blue-500!', 'bg-blue-50!');
    }, false);
});

dropZone.addEventListener('drop', (e) => {
    console.log("dropped");
    const dt = e.dataTransfer;
    const files = dt.files;
    console.log(files.length);
    if (files.length > 0) {
        fileInput.files = files;
        const event = new Event("change");
        fileInput.dispatchEvent(event);
    }
});
