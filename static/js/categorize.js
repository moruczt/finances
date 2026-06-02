let selectedTxId = null;
let currentActiveRegexRules = [];

async function selectTransaction(txId) {
    selectedTxId = txId;
    currentActiveRegexRules = [];
    
    document.querySelectorAll('[id^="tx-card-"]').forEach(el => el.classList.remove('bg-blue-50/60', 'border-l-blue-500'));
    const activeCard = document.getElementById(`tx-card-${txId}`);
    activeCard.classList.add('bg-blue-50/60', 'border-l-blue-500');
    
    const onLoad = (resp) => {
        if (resp.success) {
            populateWorkspace(resp.result.transaction);
        }
    }
    
    request(`/finances/api/transactions/${txId}`,"GET", {}, onLoad)
}

function populateWorkspace(tx) {
    document.getElementById('workspaceEmptyState').classList.add('hidden');
    const form = document.getElementById('workspaceForm');
    form.classList.remove('hidden');

    document.getElementById('wsDate').innerText = tx.date;
    document.getElementById('wsDescription').innerText = tx.description;
    document.getElementById('wsSource').innerText = tx.source_account;
    document.getElementById('wsAmount').innerText = tx.amount;

    if (window.innerWidth < 1024) {
        document.getElementById('workspaceConsole').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }

    const tbody = document.getElementById('jsonInspectorBody');
    tbody.innerHTML = "";

    Object.entries(tx.raw_json).forEach(([key, value]) => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-blue-50/30 cursor-pointer transition-colors group";
        tr.onclick = () => addRegexRuleFromCell(key, value);
        tr.innerHTML = `
            <td class="p-2 font-semibold text-gray-500 border-r border-gray-100">${key}</td>
            <td class="p-2 text-gray-900 font-medium group-hover:text-blue-600 transition-colors flex items-center justify-between">
                <span>${value}</span>
                <span class="text-[9px] bg-gray-100 text-gray-400 group-hover:bg-blue-100 group-hover:text-blue-700 font-bold px-1 rounded uppercase tracking-wider scale-90 opacity-0 group-hover:opacity-100 transition-all">+ Add Rule</span>
            </td>
        `;
        tbody.appendChild(tr);
    });

    renderActiveRules();
}

function addRegexRuleFromCell(key, value) {
    if (currentActiveRegexRules.some(r => r.key === key)) return;

    currentActiveRegexRules.push({
        key: key,
        regex: `^${value.toString()}$`
    });

    renderActiveRules();
}

function renderActiveRules() {
    const container = document.getElementById('activeRulesList');
    container.innerHTML = "";

    if (currentActiveRegexRules.length === 0) {
        container.innerHTML = `<div class="p-3 text-center border border-dashed border-gray-200 rounded-xl text-xs italic text-gray-400">No active expressions selected yet. Click cells inside raw data above.</div>`;
        return;
    }

    currentActiveRegexRules.forEach((rule, index) => {
        const card = document.createElement('div');
        card.className = "flex items-center gap-2 bg-slate-50 border border-gray-200 p-2 rounded-xl animate-fade-in";
        card.innerHTML = `
            <span class="text-[10px] font-bold font-mono text-gray-400 bg-white border border-gray-200 px-2 py-1 rounded-lg truncate max-w-30">${rule.key}</span>
            <span class="text-xs text-gray-400 font-mono font-bold">~</span>
            <input type="text" value="${rule.regex}" 
                   oninput="updateRegexValue(${index}, this.value)"
                   class="grow px-2 py-1 font-mono text-xs bg-white border border-gray-200 rounded-lg outline-none focus:border-blue-500 text-blue-600 font-semibold" />
            <button type="button" onclick="removeRegexRule(${index})" class="text-gray-400 hover:text-red-500 p-1 rounded-lg transition-colors cursor-pointer">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        `;
        container.appendChild(card);
    });
}

function updateRegexValue(index, val) {
    currentActiveRegexRules[index].regex = val;
}

function removeRegexRule(index) {
    currentActiveRegexRules.splice(index, 1);
    renderActiveRules();
}


function handleAddNewCategoryInline() {
    const select = document.getElementById('categorySelect');
    const selectedOption = select.options[select.selectedIndex];
    const parentPath = selectedOption.getAttribute('data-path');
    const newName = document.getElementById('newCategoryName').value.trim();

    if(!newName) {
        showToast("Please define a sub-hierarchy category first.", "info");
        return;
    }

    const data = {
        "parentPath": parentPath,
        "category": newName,
    };

    const onLoad = (resp) => {
        if (resp.success) {
            const completeGeneratedPath = `${parentPath}:${newName}`;
            const newOpt = document.createElement('option');
            const mockGeneratedId = Math.floor(Math.random() * 1000) + 500; // Mock ID assignment
            newOpt.value = mockGeneratedId;
            newOpt.text = completeGeneratedPath;
            newOpt.setAttribute('data-path', completeGeneratedPath);
            newOpt.selected = true;
            select.add(newOpt);
            document.getElementById('newCategoryName').value = "";
            select.dispatchEvent(new Event('change'));
        }
    }

    request(`/finances/api/categories`,"POST", data, onLoad)
}

function cancelWorkspace() {
    document.getElementById('workspaceForm').classList.add('hidden');
    document.getElementById('workspaceEmptyState').classList.remove('hidden');
    document.querySelectorAll('[id^="tx-card-"]').forEach(el => el.classList.remove('bg-blue-50/60', 'border-l-blue-500'));
}

function commitMappingRule() {
    const targetAccountId = document.getElementById('categorySelect').value;
    
    if(!targetAccountId) {
        showToast("Please assign a destination target category balance first.", "info");
        return;
    }

    const data = {
        "transaction_id": selectedTxId,
        "target_account_id": targetAccountId,
        "rules": {}
    };
    for (key in currentActiveRegexRules) {
        data["rules"][key] = currentActiveRegexRules[key];
    }

    const onLoad = (resp) => {
        if (resp.success) {
            // globalThis.location.reload();
        }
    }
    
    request(`/finances/api/rules`,"POST", data, onLoad)
}


// PAGE LOAD SCRIPTS

const select = document.getElementById('categorySelect');
const prefixLabel = document.getElementById('newCategoryParentPrefix');

select.addEventListener('change', () => {
    const selectedOption = select.options[select.selectedIndex];
    const activePath = selectedOption.getAttribute('data-path');
    prefixLabel.innerText = activePath ? activePath + ":" : "Root:";
});