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

        // Accumulated selection: [{ id, file }] with a stable per-selection id
        let selectedEntries = [];
        let nextEntryId = 1;

        function addFilesToSelection(files) {
            for (const file of files) {
                selectedEntries.push({ id: nextEntryId++, file: file });
            }
        }

        function removeEntryById(entryId) {
            selectedEntries = selectedEntries.filter(entry => entry.id !== entryId);
        }

        function syncInputFromSelection() {
            const dt = new DataTransfer();
            for (const entry of selectedEntries) dt.items.add(entry.file);
            fileInput.files = dt.files;
        }

        function renderFileList() {
            if (!fileList) return;
            fileList.innerHTML = '';
            if (selectedEntries.length === 0) {
                if (fileListContainer) fileListContainer.style.display = 'none';
                if (fileListStatus) fileListStatus.textContent = 'No files selected.';
                return;
            }
            if (fileListContainer) fileListContainer.style.display = 'block';
            for (const entry of selectedEntries) {
                const file = entry.file;
                const item = document.createElement('li');
                item.className = 'list-group-item d-flex justify-content-between align-items-center';
                const nameSpan = document.createElement('span');
                nameSpan.textContent = file.name;
                const removeButton = document.createElement('button');
                removeButton.type = 'button';
                removeButton.className = 'btn-remove-file';
                removeButton.dataset.entryId = String(entry.id);
                removeButton.setAttribute('aria-label', 'Remove ' + file.name);
                removeButton.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
                const sizeBadge = document.createElement('span');
                sizeBadge.className = 'badge badge-gold rounded-pill';
                sizeBadge.textContent = formatSize(file.size);
                const rightGroup = document.createElement('span');
                rightGroup.className = 'd-flex align-items-center gap-2';
                rightGroup.appendChild(sizeBadge);
                rightGroup.appendChild(removeButton);
                item.appendChild(nameSpan);
                item.appendChild(rightGroup);
                fileList.appendChild(item);
            }
            if (fileListStatus) {
                fileListStatus.textContent = selectedEntries.length + (selectedEntries.length === 1 ? ' file selected.' : ' files selected.');
            }
        }

        // Initial state
        if (fileListContainer) fileListContainer.style.display = 'none';
        uploadStatus.classList.add('d-none');
        uploadStatus.hidden = true;
        if (processingNote) {
            processingNote.classList.add('d-none');
            processingNote.hidden = true;
        }

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length === 0) return;
            addFilesToSelection(fileInput.files);
            syncInputFromSelection();
            renderFileList();
        });

        if (fileList) {
            fileList.addEventListener('click', (e) => {
                const button = e.target.closest('.btn-remove-file');
                if (!button || !fileList.contains(button)) return;
                removeEntryById(Number(button.dataset.entryId));
                syncInputFromSelection();
                renderFileList();
            });
        }

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
                    addFilesToSelection(droppedFiles);
                    syncInputFromSelection();
                    renderFileList();
                }
            });
        }

        if (uploadForm) {
            uploadForm.addEventListener('submit', () => {
                uploadButton.disabled = true;
                uploadButton.value = 'Processing...';
                uploadStatus.classList.remove('d-none');
                uploadStatus.hidden = false;
                if (processingNote) {
                    processingNote.classList.remove('d-none');
                    processingNote.hidden = false;
                }
            });
        }

        window.addEventListener('pageshow', () => {
            uploadButton.disabled = false;
            uploadButton.value = 'Upload Files';
            uploadStatus.classList.add('d-none');
            uploadStatus.hidden = true;
            if (processingNote) {
                processingNote.classList.add('d-none');
                processingNote.hidden = true;
            }
            if (fileInput.files.length === 0) {
                selectedEntries = [];
                renderFileList();
            }
        });
    }

    const passwordToggles = document.querySelectorAll('[data-password-toggle]');
    if (passwordToggles.length > 0) {
        passwordToggles.forEach(button => {
            button.addEventListener('click', () => {
                const input = document.getElementById(button.dataset.passwordToggle);
                if (!input) return;

                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                button.textContent = isHidden ? 'Hide' : 'Show';
                button.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
                button.setAttribute('aria-pressed', String(isHidden));
            });
        });
    }
    // ========================
    // Similarity Threshold Slider (index.html)
    // ========================
    const thresholdSlider = document.getElementById('thresholdSlider');
    const thresholdDisplay = document.getElementById('thresholdDisplay');

    if (thresholdSlider && thresholdDisplay) {

        function updateThresholdDisplay() {
            const value = parseFloat(thresholdSlider.value);

            thresholdDisplay.textContent = value.toFixed(2);

            thresholdSlider.setAttribute(
                'aria-valuenow',
                value.toFixed(2)
            );

            let label = 'Custom';

            if (Math.abs(value - 0.25) < 0.001) {
                label = 'High Sensitivity';
            } else if (Math.abs(value - 0.30) < 0.001) {
                label = 'Balanced';
            } else if (Math.abs(value - 0.35) < 0.001) {
                label = 'Strict';
            }

            thresholdSlider.setAttribute(
                'aria-valuetext',
                `${label} (${value.toFixed(2)})`
            );
        }

        thresholdSlider.addEventListener(
            'input',
            updateThresholdDisplay
        );

        // Set initial display
        updateThresholdDisplay();
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