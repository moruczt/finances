async function addRootAccount(btn) {
    const side = btn.dataset.side;

    const name = await showPrompt("Add Top-Level Account", `Create a new top-level account under "${side}".`, '', 'Create');
    if (!name) return;

    const onLoad = (resp) => {
        if (resp.success) {
            globalThis.location.reload();
        }
    }

    request(`${ROOT_PATH}/api/accounts/roots/${side}/children`, "POST", {"name":name}, onLoad);
}

async function addChildAccount(btn) {
    const parentId = btn.dataset.accountId;
    const parentPath = btn.dataset.path;

    const name = await showPrompt("Add Child Account", `Create a new account under "${parentPath}".`, '', 'Create');
    if (!name) return;

    const onLoad = (resp) => {
        if (resp.success) {
            globalThis.location.reload();
        }
    }

    request(`${ROOT_PATH}/api/accounts/${parentId}/children`, "POST", {"name":name}, onLoad);
}

async function renameAccount(btn) {
    const accountId = btn.dataset.accountId;
    const currentName = document.getElementById(`account-name-${accountId}`).textContent.trim();

    const name = await showPrompt("Rename Account", "Enter a new name for this account.", currentName, 'Save');
    if (!name || name === currentName) return;

    const onLoad = (resp) => {
        if (resp.success) {
            globalThis.location.reload();
        }
    }

    request(`${ROOT_PATH}/api/accounts/${accountId}`, "PATCH", {"name":name}, onLoad);
}
