async function wipeDatabase() {
    const confirmed = await showConfirm("Wipe Entire Database?",
                                        "This will permanently purge all transactions, double-entry ledgers, and raw import logs. This process is irreversible.",
                                        "Yes, Purge All Data");

    if (!confirmed) return;

    const onLoad = (resp) => {
        if (resp.success) {
            globalThis.location.reload();
        }
    }

    request('/finances/api/wipe',"DELETE", {}, onLoad)
}