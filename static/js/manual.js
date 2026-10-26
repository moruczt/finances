const form = document.getElementById('manualForm');
const amountInput = document.getElementById('amountInput');
const descriptionInput = document.getElementById('descriptionInput');
const monthInput = document.getElementById('monthInput');
const monthsInput = document.getElementById('monthsInput');
const splitHint = document.getElementById('splitHint');
const addBtn = document.getElementById('addBtn');
const overviewEl = document.getElementById('manualOverview');

let viewedMonth = new URLSearchParams(location.search).get('month') || monthInput.value;

function renderOverview(result) {
    overviewEl.innerHTML = result.html;
    viewedMonth = result.month;
    const url = new URL(location.href);
    url.searchParams.set('month', viewedMonth);
    history.replaceState(null, '', url);
}

function updateSplitHint() {
    const months = parseInt(monthsInput.value, 10) || 1;
    const amount = parseFloat(amountInput.value) || 0;
    if (months <= 1) {
        splitHint.classList.add('hidden');
        return;
    }
    const part = Math.floor(amount / months);
    splitHint.textContent = `${months} entries of ~${part.toLocaleString('hu-HU')} HUF, starting ${monthInput.value}`;
    splitHint.classList.remove('hidden');
}
[amountInput, monthInput, monthsInput].forEach(el => el.addEventListener('input', updateSplitHint));

form.addEventListener('submit', (e) => {
    e.preventDefault();
    addBtn.disabled = true;

    const data = {
        amount: amountInput.value,
        description: descriptionInput.value,
        month: monthInput.value,
        budget_id: parseInt(form.querySelector('input[name="budget"]:checked').value, 10),
        months: parseInt(monthsInput.value, 10) || 1,
    };

    const onLoad = (resp) => {
        addBtn.disabled = false;
        if (!resp.success) return;
        renderOverview(resp.result);
        amountInput.value = '';
        descriptionInput.value = '';
        monthsInput.value = 1;
        updateSplitHint();
        amountInput.focus();
    }

    request(`${ROOT_PATH}/api/manual-entries`, "POST", data, onLoad);
});

// The overview is re-rendered after every change, so its buttons are handled by delegation.
overviewEl.addEventListener('click', async (e) => {
    const navBtn = e.target.closest('.month-nav');
    if (navBtn) {
        const onLoad = (resp) => { if (resp.success) renderOverview(resp.result); }
        request(`${ROOT_PATH}/api/manual-overview?month=${navBtn.dataset.month}`, "GET", {}, onLoad);
        return;
    }

    const deleteBtn = e.target.closest('.entry-delete');
    if (deleteBtn) {
        const parts = parseInt(deleteBtn.dataset.parts, 10);
        const message = parts > 1 ? `This entry is split across ${parts} months. All ${parts} parts will be deleted.` : 'This entry will be deleted.';
        if (!await showConfirm('Delete entry?', message, 'Delete')) return;
        const onLoad = (resp) => { if (resp.success) renderOverview(resp.result); }
        request(`${ROOT_PATH}/api/manual-entries/${deleteBtn.dataset.entryId}?month=${viewedMonth}`, "DELETE", {}, onLoad);
        return;
    }

    const limitBtn = e.target.closest('.budget-limit');
    if (limitBtn) {
        const value = await showPrompt(`${escapeHtml(limitBtn.dataset.budgetName)} limit`, 'Monthly limit in HUF. Use 0 for no limit.', limitBtn.dataset.limit);
        if (value === null) return;
        const limit = parseFloat(value.replace(/\s/g, ''));
        if (Number.isNaN(limit) || limit < 0) {
            showToast('Invalid limit');
            return;
        }
        const onLoad = (resp) => { if (resp.success) renderOverview(resp.result); }
        request(`${ROOT_PATH}/api/budgets/${limitBtn.dataset.budgetId}?month=${viewedMonth}`, "PATCH", {monthly_limit: limit}, onLoad);
    }
});
