function toggleDetails(rowId) {
    const detailsRow = document.getElementById(`details-${rowId}`);
    const chevron = document.getElementById(`chevron-${rowId}`);
    
    if (detailsRow.classList.contains('hidden')) {
        detailsRow.classList.remove('hidden');
        chevron.classList.add('rotate-90', 'text-gray-700');
    } else {
        detailsRow.classList.add('hidden');
        chevron.classList.remove('rotate-90', 'text-gray-700');
    }
}