document.addEventListener('DOMContentLoaded', () => {
    console.log('HAUdemicCheck frontend loaded');

    // ========================
    // 1. Drop zone (index.html) – only if #files exists
    // ========================
    const fileInput = document.getElementById('files');
    if (fileInput) {
        const dropZone = document.getElementById('dropZone');
        const fileList = document.getElementById('selectedFiles');
        const fileListStatus = document.getElementById('selectedFilesStatus');
        const fileListContainer = document.getElementById('selectedFilesContainer');
        const uploadButton = document.getElementById('uploadButton');
        const uploadStatus = document.getElementById('uploadStatus');
        const processingNote = document.getElementById('processingNote');
        const uploadForm = fileInput.closest('form');

        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }

        function renderFileList(files) {
            if (!fileList) return;
            fileList.innerHTML = '';
            if (!files || files.length === 0) {
                if (fileListContainer) fileListContainer.style.display = 'none';
                if (fileListStatus) fileListStatus.textContent = 'No files selected.';
                return;
            }
            if (fileListContainer) fileListContainer.style.display = 'block';
            for (const file of files) {
                const item = document.createElement('li');
                item.className = 'list-group-item d-flex justify-content-between align-items-center';
                const nameSpan = document.createElement('span');
                nameSpan.textContent = file.name;
                const sizeBadge = document.createElement('span');
                sizeBadge.className = 'badge badge-gold rounded-pill';
                sizeBadge.textContent = formatSize(file.size);
                item.appendChild(nameSpan);
                item.appendChild(sizeBadge);
                fileList.appendChild(item);
            }
            if (fileListStatus) {
                fileListStatus.textContent = files.length + (files.length === 1 ? ' file selected.' : ' files selected.');
            }
        }

        // Initial state
        if (fileListContainer) fileListContainer.style.display = 'none';
        uploadStatus.style.display = 'none';

        fileInput.addEventListener('change', () => renderFileList(fileInput.files));

        if (dropZone) {
            ['dragenter', 'dragover'].forEach(ev => {
                dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add('drop-zone-active'); });
            });
            ['dragleave', 'drop'].forEach(ev => {
                dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove('drop-zone-active'); });
            });
            dropZone.addEventListener('drop', (e) => {
                const droppedFiles = e.dataTransfer.files;
                if (droppedFiles.length > 0) {
                    const dt = new DataTransfer();
                    for (const file of droppedFiles) dt.items.add(file);
                    fileInput.files = dt.files;
                    renderFileList(fileInput.files);
                }
            });
        }

        if (uploadForm) {
            uploadForm.addEventListener('submit', () => {
                uploadButton.disabled = true;
                uploadButton.value = 'Processing...';
                uploadStatus.style.display = 'flex';
                if (processingNote) processingNote.style.display = 'block';
            });
        }

        window.addEventListener('pageshow', () => {
            uploadButton.disabled = false;
            uploadButton.value = 'Upload Files';
            uploadStatus.style.display = 'none';
            if (processingNote) processingNote.style.display = 'none';
            if (fileInput.files.length === 0) renderFileList([]);
        });
    }

    // ========================
    // 2. Dashboard table (dashboard.html) – only if #analysesTable exists
    // ========================
    const table = document.getElementById('analysesTable');
    if (table) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        const searchInput = document.getElementById('tableSearch');
        const noResultsMessage = document.getElementById('noResultsMessage');
        const filterButtons = document.querySelectorAll('[data-filter-status]');
        const clearSearch = document.getElementById('clearSearch');

        let activeFilter = null;

        function applyFilters() {
            const query = (searchInput?.value || '').toLowerCase().trim();
            let visibleCount = 0;

            rows.forEach(row => {
                const firstCell = row.querySelector('td');
                const filename = firstCell?.dataset.value?.toLowerCase() || '';
                const matchesSearch = !query || filename.includes(query);
                const matchesFilter = !activeFilter || row.dataset.status === activeFilter;
                const show = matchesSearch && matchesFilter;

                row.style.display = show ? '' : 'none';
                if (show) visibleCount++;
            });

            if (noResultsMessage) {
                noResultsMessage.style.display = visibleCount === 0 ? 'block' : 'none';
            }
        }

        if (searchInput) {
            searchInput.addEventListener('input', applyFilters);
        }
        if (clearSearch) {
            clearSearch.addEventListener('click', () => {
                searchInput.value = '';
                applyFilters();
            });
        }

        filterButtons.forEach(button => {
            button.addEventListener('click', () => {
                const status = button.dataset.filterStatus;
                activeFilter = (activeFilter === status) ? null : status;

                filterButtons.forEach(b => {
                    b.classList.toggle('filter-active', b.dataset.filterStatus === activeFilter);
                });

                table.scrollIntoView({ behavior: 'smooth', block: 'start' });
                applyFilters();
            });
        });

        // Column sorting
        table.querySelectorAll('th[data-sort]').forEach((th, index) => {
            const button = th.querySelector('.sort-btn');
            if (!button) return;
            const icon = button.querySelector('i');

            button.addEventListener('click', () => {
                const currentDir = th.getAttribute('aria-sort');
                const nextDir = currentDir === 'ascending' ? 'descending' : 'ascending';

                table.querySelectorAll('th[data-sort]').forEach(h => {
                    h.setAttribute('aria-sort', 'none');
                    const i = h.querySelector('.sort-btn i');
                    if (i) i.className = 'bi bi-arrow-down-up';
                });

                th.setAttribute('aria-sort', nextDir);
                if (icon) {
                    icon.className = nextDir === 'ascending' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
                }

                const type = th.dataset.sort;
                const sorted = rows.slice().sort((a, b) => {
                    const aVal = a.children[index]?.dataset?.value || '';
                    const bVal = b.children[index]?.dataset?.value || '';
                    let comparison;
                    if (type === 'numeric') {
                        comparison = parseFloat(aVal) - parseFloat(bVal);
                    } else {
                        comparison = aVal.localeCompare(bVal);
                    }
                    return nextDir === 'ascending' ? comparison : -comparison;
                });

                sorted.forEach(row => tbody.appendChild(row));
            });
        });
    }
});