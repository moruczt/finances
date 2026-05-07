async function rawImport(e) {
    e.target.disabled = true;
    document.getElementById("spinner").classList.remove("hidden");

    const file = e.target.files[0];
    const accountId = document.getElementById("accountSelect").value;
    if (!file) {
        showToast("No file was uploaded", "info");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const onLoad = (resp) => {
        if (resp.success) {

        }
        e.target.disabled = false;
        document.getElementById("spinner").classList.add("hidden");
    }


    request(`/finances/api/accounts/${accountId}/import`,"POST", formData, onLoad, "formData")

}


document.getElementById("fileInput").addEventListener("change", rawImport);