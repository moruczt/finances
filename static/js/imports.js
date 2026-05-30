async function wipeDatabase() {
    const confirmed = await showConfirm(
        title= "Wipe Entire Database?",
        message= "This will permanently purge all transactions, double-entry ledgers, and raw import logs. This process is irreversible.",
        confirmText= "Yes, Purge All Data"
    );

    if (!confirmed) return;

    const onLoad = (resp) => {
        if (resp.success) {
            window.location.reload();
        }
    }

    request('/finances/api/wipe',"DELETE", {}, onLoad)
}