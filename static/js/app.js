/**
 * Page2PDF — Frontend Application
 * Handles multi-URL collections, API communication, drag-and-drop, and downloads.
 */

(function () {
    'use strict';

    // ── DOM Elements ────────────────────────────────────────────
    const urlInput = document.getElementById('url-input');
    const addUrlBtn = document.getElementById('add-url-btn');
    const errorMessage = document.getElementById('error-message');
    const urlListContainer = document.getElementById('url-list-container');
    const urlList = document.getElementById('url-list');
    const generateAllBtn = document.getElementById('generate-all-btn');
    
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsPanel = document.getElementById('settings-panel');
    const progressSection = document.getElementById('progress-section');
    const heroSection = document.getElementById('home');
    
    const progressTitle = document.getElementById('progress-title');
    const progressSubtitle = document.getElementById('progress-subtitle');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressSpinner = document.getElementById('progress-spinner');
    const progressCheck = document.getElementById('progress-check');
    const progressSteps = document.getElementById('progress-steps');
    
    const downloadSection = document.getElementById('download-section');
    const dlSources = document.getElementById('dl-sources');
    const dlPages = document.getElementById('dl-pages');
    const dlSize = document.getElementById('dl-size');
    const downloadFilename = document.getElementById('download-filename');
    const downloadBtn = document.getElementById('download-btn');
    const individualDownloadsList = document.getElementById('individual-downloads-list');
    const newBtn = document.getElementById('new-btn');
    const errorSection = document.getElementById('error-section');
    const errorDetail = document.getElementById('error-detail');
    const retryBtn = document.getElementById('retry-btn');
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    // Page Management Elements
    const pmSection = document.getElementById('page-management-section');
    const pmTotal = document.getElementById('pm-total');
    const pmKept = document.getElementById('pm-kept');
    const pmRemoved = document.getElementById('pm-removed');
    const pmThumbnailsGrid = document.getElementById('pm-thumbnails-grid');
    const pmBtnRemoveLast = document.getElementById('pm-btn-remove-last');
    const pmBtnRemoveSelected = document.getElementById('pm-btn-remove-selected');
    const pmBtnKeepSelected = document.getElementById('pm-btn-keep-selected');
    const pmBtnRestoreAll = document.getElementById('pm-btn-restore-all');
    const pmBtnInsertFile = document.getElementById('pm-btn-insert-file');
    const insertFileModal = document.getElementById('insert-file-modal');
    const closeInsertModal = document.getElementById('close-insert-modal');
    const insertFileInput = document.getElementById('insert-file-input');
    const insertPositionSelect = document.getElementById('insert-position-select');
    const insertPageNumberContainer = document.getElementById('insert-page-number-container');
    const insertPageNumber = document.getElementById('insert-page-number');
    const btnConfirmInsert = document.getElementById('btn-confirm-insert');
    const insertErrorMessage = document.getElementById('insert-error-message');
    
    const pmRangeInput = document.getElementById('pm-range-input');
    const pmBtnApplyRange = document.getElementById('pm-btn-apply-range');
    const pmErrorMessage = document.getElementById('pm-error-message');
    const pmBtnPreview = document.getElementById('pm-btn-preview');
    const pmBtnContinue = document.getElementById('pm-btn-continue');
    
    let totalPagesCount = 0;
    let pageStates = []; // true = keep, false = remove
    let pageSelections = []; // true = selected in UI, false = not selected
    let pageRotations = {}; // originalPageIndex -> degrees (90, 180, 270)
    let pageOrder = []; // array of original page indices in current order

    // Settings
    const settingTitle = document.getElementById('setting-title');
    const settingAuthor = document.getElementById('setting-author');
    const settingPageSize = document.getElementById('setting-page-size');
    const settingFontSize = document.getElementById('setting-font-size');
    const settingFontFamily = document.getElementById('setting-font-family');
    const settingImages = document.getElementById('setting-images');
    const settingLinks = document.getElementById('setting-links');
    const settingToc = document.getElementById('setting-toc');
    const settingCode = document.getElementById('setting-code');
    const settingCover = document.getElementById('setting-cover');
    const settingSeparator = document.getElementById('setting-separator');
    
    // Modal Elements
    const imageModal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    const closeModalBtn = document.getElementById('close-modal');
    const modalLoader = document.getElementById('modal-loader');

    let currentCollectionId = null;
    let pollInterval = null;
    let collectionItems = []; // Local cache of items for rendering

    // ── Navigation & Setup ──────────────────────────────────────
    navToggle.addEventListener('click', () => {
        navLinks.classList.toggle('open');
    });

    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => navLinks.classList.remove('open'));
    });

    settingsToggle.addEventListener('click', () => {
        settingsToggle.classList.toggle('active');
        settingsPanel.classList.toggle('open');
    });

    document.querySelectorAll('.example-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            urlInput.value = chip.dataset.url;
            urlInput.focus();
            clearError();
        });
    });

    const pdfUploadInput = document.getElementById('pdf-upload-input');

    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addUrlToCollection();
        }
    });

    urlInput.addEventListener('input', clearError);
    addUrlBtn.addEventListener('click', addUrlToCollection);
    generateAllBtn.addEventListener('click', startGeneration);
    
    // PDF File Upload Handler
    pdfUploadInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showError("Only PDF files are supported.");
            return;
        }

        // Initialize collection if it doesn't exist
        if (!currentCollectionId) {
            try {
                const res = await fetch('/api/collections', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: "My PDF Collection" })
                });
                const data = await res.json();
                if (data.success) {
                    currentCollectionId = data.collection.id;
                } else {
                    showError("Failed to initialize collection.");
                    return;
                }
            } catch (err) {
                showError("Unable to connect to the server.");
                return;
            }
        }
        
        // Add loading placeholder to UI
        const tempId = 'upload_' + Date.now();
        collectionItems.push({ id: tempId, url: file.name, title: "Uploading...", status: 'queued' });
        renderUrlList();
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const res = await fetch(`/api/collections/${currentCollectionId}/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                collectionItems = data.collection.items;
                renderUrlList();
                e.target.value = ''; // Reset input
            } else {
                showError(data.error || "Failed to upload PDF.");
                collectionItems = collectionItems.filter(item => item.id !== tempId);
                renderUrlList();
            }
        } catch (err) {
            showError("Upload failed due to a network error.");
            collectionItems = collectionItems.filter(item => item.id !== tempId);
            renderUrlList();
        }
    });

    newBtn.addEventListener('click', resetToHome);
    retryBtn.addEventListener('click', () => {
        errorSection.classList.remove('active');
        progressSection.classList.remove('active');
        heroSection.style.display = '';
        document.querySelector('.how-it-works').style.display = '';
        document.querySelector('.features').style.display = '';
        document.querySelector('.about').style.display = '';
    });
    
    // Page Management Events
    pmBtnRemoveLast.addEventListener('click', () => {
        if (totalPagesCount > 0) {
            let lastIdx = -1;
            for(let i = pageStates.length - 1; i >= 0; i--) {
                if (pageStates[i]) {
                    lastIdx = i;
                    break;
                }
            }
            if (lastIdx !== -1) {
                pageStates[lastIdx] = false;
                updatePmUI();
            }
        }
    });
    
    pmBtnRemoveSelected.addEventListener('click', () => {
        for(let i = 0; i < totalPagesCount; i++) {
            if (pageSelections[i]) {
                pageStates[i] = false;
                pageSelections[i] = false;
            }
        }
        updatePmUI();
    });
    
    pmBtnKeepSelected.addEventListener('click', () => {
        let hasSelection = pageSelections.some(s => s);
        if(!hasSelection) return;
        
        for(let i = 0; i < totalPagesCount; i++) {
            if (pageSelections[i]) {
                pageStates[i] = true;
                pageSelections[i] = false;
            } else {
                pageStates[i] = false;
            }
        }
        updatePmUI();
    });
    
    pmBtnRestoreAll.addEventListener('click', () => {
        for(let i = 0; i < totalPagesCount; i++) {
            pageStates[i] = true;
            pageSelections[i] = false;
        }
        pmRangeInput.value = '';
        pmErrorMessage.textContent = '';
        updatePmUI();
    });

    // Insert File Modal Events
    pmBtnInsertFile.addEventListener('click', () => {
        insertFileModal.style.display = 'flex';
        insertErrorMessage.textContent = '';
        insertFileInput.value = '';
        insertPositionSelect.value = 'end';
        insertPageNumberContainer.style.display = 'none';
        insertPageNumber.value = '';
    });
    
    closeInsertModal.addEventListener('click', () => {
        insertFileModal.style.display = 'none';
    });
    
    insertPositionSelect.addEventListener('change', (e) => {
        if (e.target.value === 'after') {
            insertPageNumberContainer.style.display = 'block';
        } else {
            insertPageNumberContainer.style.display = 'none';
        }
    });
    
    btnConfirmInsert.addEventListener('click', async () => {
        const file = insertFileInput.files[0];
        if (!file) {
            insertErrorMessage.textContent = 'Please select a file to insert.';
            return;
        }
        
        const position = insertPositionSelect.value;
        const pageIndexStr = insertPageNumber.value;
        let pageIndex = 0;
        
        if (position === 'after') {
            pageIndex = parseInt(pageIndexStr);
            if (isNaN(pageIndex) || pageIndex < 1 || pageIndex > totalPagesCount) {
                insertErrorMessage.textContent = 'Please enter a valid page number (1 to ' + totalPagesCount + ').';
                return;
            }
            // 0-indexed adjustment for backend
            pageIndex = pageIndex - 1; 
        }
        
        btnConfirmInsert.disabled = true;
        btnConfirmInsert.querySelector('.btn-text').textContent = 'Inserting...';
        insertErrorMessage.textContent = '';
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('position', position);
        formData.append('page_index', pageIndex);
        
        try {
            const res = await fetch(`/api/collections/${currentCollectionId}/insert-file`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (data.success) {
                insertFileModal.style.display = 'none';
                showCompleted(data.collection);
            } else {
                insertErrorMessage.textContent = data.error || 'Failed to insert file.';
            }
        } catch (err) {
            insertErrorMessage.textContent = 'Network error occurred.';
        } finally {
            btnConfirmInsert.disabled = false;
            btnConfirmInsert.querySelector('.btn-text').textContent = 'Insert File';
        }
    });
    
    pmBtnApplyRange.addEventListener('click', applyCustomRange);
    pmBtnPreview.addEventListener('click', applyPageEdits);
    pmBtnContinue.addEventListener('click', () => {
        pmSection.style.display = 'none';
        downloadSection.classList.add('active');
    });
    
    // Modal Events
    closeModalBtn.addEventListener('click', () => {
        imageModal.style.display = 'none';
        modalImg.src = '';
    });
    imageModal.addEventListener('click', (e) => {
        if(e.target === imageModal) {
            imageModal.style.display = 'none';
            modalImg.src = '';
        }
    });

    // ── Utility ─────────────────────────────────────────────────

    function clearError() {
        errorMessage.textContent = '';
    }

    function showError(msg) {
        errorMessage.textContent = msg;
    }

    function normalizeUrl(url) {
        url = url.trim();
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            url = 'https://' + url;
        }
        return url;
    }

    // ── Collection Management ───────────────────────────────────

    async function ensureCollection() {
        if (currentCollectionId) return true;
        
        try {
            const res = await fetch('/api/collections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: settingTitle.value.trim() || 'Study Material Collection' })
            });
            const data = await res.json();
            if (data.success) {
                currentCollectionId = data.collection.id;
                return true;
            }
            return false;
        } catch (e) {
            console.error('Failed to create collection', e);
            return false;
        }
    }

    async function addUrlToCollection() {
        const rawUrl = urlInput.value.trim();
        if (!rawUrl) {
            showError('Please enter a webpage URL.');
            urlInput.focus();
            return;
        }

        const url = normalizeUrl(rawUrl);
        clearError();
        addUrlBtn.disabled = true;

        if (!(await ensureCollection())) {
            showError('Failed to initialize collection. Please try again.');
            addUrlBtn.disabled = false;
            return;
        }

        try {
            const res = await fetch(`/api/collections/${currentCollectionId}/urls`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();
            
            if (data.success) {
                urlInput.value = '';
                collectionItems = data.collection.items;
                renderUrlList();
            } else {
                showError(data.error || 'Failed to add URL.');
            }
        } catch (e) {
            console.error('Error adding URL', e);
            showError('Network error while adding URL.');
        } finally {
            addUrlBtn.disabled = false;
        }
    }

    async function removeUrl(itemId) {
        try {
            const res = await fetch(`/api/collections/${currentCollectionId}/urls/${itemId}`, {
                method: 'DELETE'
            });
            const data = await res.json();
            if (data.success) {
                collectionItems = data.collection.items;
                renderUrlList();
            }
        } catch (e) {
            console.error('Error removing URL', e);
        }
    }

    async function moveUrl(itemId, direction) {
        const idx = collectionItems.findIndex(i => i.id === itemId);
        if (idx === -1) return;
        
        if (direction === 'up' && idx > 0) {
            const temp = collectionItems[idx - 1];
            collectionItems[idx - 1] = collectionItems[idx];
            collectionItems[idx] = temp;
        } else if (direction === 'down' && idx < collectionItems.length - 1) {
            const temp = collectionItems[idx + 1];
            collectionItems[idx + 1] = collectionItems[idx];
            collectionItems[idx] = temp;
        } else {
            return; // No change
        }
        
        renderUrlList();
        saveOrder();
    }

    async function saveOrder() {
        if (!currentCollectionId) return;
        const itemIds = collectionItems.map(i => i.id);
        
        try {
            await fetch(`/api/collections/${currentCollectionId}/urls/reorder`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_ids: itemIds })
            });
        } catch (e) {
            console.error('Failed to save order', e);
        }
    }

    // ── Drag and Drop ───────────────────────────────────────────
    let draggedItem = null;

    function initDragAndDrop() {
        const items = document.querySelectorAll('.url-item');
        items.forEach(item => {
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragover', handleDragOver);
            item.addEventListener('drop', handleDrop);
            item.addEventListener('dragend', handleDragEnd);
        });
    }

    function handleDragStart(e) {
        draggedItem = this;
        this.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', this.dataset.id);
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        return false;
    }

    function handleDrop(e) {
        e.stopPropagation();
        if (draggedItem !== this) {
            const draggedId = draggedItem.dataset.id;
            const targetId = this.dataset.id;
            
            const draggedIdx = collectionItems.findIndex(i => i.id === draggedId);
            const targetIdx = collectionItems.findIndex(i => i.id === targetId);
            
            const item = collectionItems.splice(draggedIdx, 1)[0];
            collectionItems.splice(targetIdx, 0, item);
            
            renderUrlList();
            saveOrder();
        }
        return false;
    }

    function handleDragEnd() {
        this.classList.remove('dragging');
        draggedItem = null;
    }


    function renderUrlList() {
        urlList.innerHTML = '';
        
        if (collectionItems.length === 0) {
            urlListContainer.style.display = 'none';
            return;
        }
        
        urlListContainer.style.display = 'block';
        
        collectionItems.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'url-item';
            div.draggable = true;
            div.dataset.id = item.id;
            
            div.innerHTML = `
                <div class="url-item-drag-handle" title="Drag to reorder">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line>
                    </svg>
                </div>
                <div class="url-item-content">
                    <div class="url-item-title">${item.title || 'Loading...'}</div>
                    <div class="url-item-url">${item.url}</div>
                </div>
                <div class="url-item-actions">
                    <button class="url-action-btn" onclick="document.dispatchEvent(new CustomEvent('moveUrl', {detail: {id: '${item.id}', dir: 'up'}}))" ${index === 0 ? 'disabled style="opacity:0.3"' : ''}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                    </button>
                    <button class="url-action-btn" onclick="document.dispatchEvent(new CustomEvent('moveUrl', {detail: {id: '${item.id}', dir: 'down'}}))" ${index === collectionItems.length - 1 ? 'disabled style="opacity:0.3"' : ''}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>
                    <button class="url-action-btn delete" onclick="document.dispatchEvent(new CustomEvent('removeUrl', {detail: '${item.id}'}))">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"></path><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;
            urlList.appendChild(div);
        });
        
        initDragAndDrop();
    }

    // Bind custom events from inline handlers
    document.addEventListener('moveUrl', (e) => moveUrl(e.detail.id, e.detail.dir));
    document.addEventListener('removeUrl', (e) => removeUrl(e.detail));

    // ── Generation Flow ─────────────────────────────────────────

    async function startGeneration() {
        if (!currentCollectionId || collectionItems.length === 0) return;

        const request = {
            page_size: settingPageSize.value,
            font_size: settingFontSize.value,
            font_family: settingFontFamily.value,
            include_images: settingImages.checked,
            include_links: settingLinks.checked,
            include_toc: settingToc.checked,
            include_code: settingCode.checked,
        };

        showProgressSection();

        try {
            const response = await fetch(`/api/collections/${currentCollectionId}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request),
            });

            const data = await response.json();
            if (!data.success) {
                showJobError(data.error || 'Failed to start generation.');
                return;
            }

            startPolling();
        } catch (err) {
            console.error('Generation request failed:', err);
            showJobError('Unable to connect to the server.');
        }
    }

    function showProgressSection() {
        heroSection.style.display = 'none';
        document.querySelector('.how-it-works').style.display = 'none';
        document.querySelector('.features').style.display = 'none';
        document.querySelector('.about').style.display = 'none';

        progressSection.classList.add('active');
        downloadSection.classList.remove('active');
        errorSection.classList.remove('active');

        progressSpinner.style.display = 'block';
        progressCheck.style.display = 'none';
        progressTitle.textContent = 'Generating PDFs...';
        progressSubtitle.textContent = `Processing ${collectionItems.length} source(s)`;
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        
        progressSteps.innerHTML = ''; // Will fill via polling
    }

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(pollStatus, 1000);
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }

    async function pollStatus() {
        if (!currentCollectionId) return;

        try {
            const response = await fetch(`/api/collections/${currentCollectionId}/status`);
            const data = await response.json();
            
            if (data.success && data.collection) {
                updateProgress(data.collection);

                if (data.collection.status === 'completed' || data.collection.status === 'failed') {
                    stopPolling();
                    if (data.collection.status === 'completed') {
                        triggerMerge(data.collection);
                    } else {
                        // Show retry option for partial failures
                        const successCount = data.collection.items.filter(i => i.status === 'completed').length;
                        if (successCount > 0) {
                            if(confirm(`Only ${successCount} of ${data.collection.items.length} PDFs generated successfully. Do you want to merge the available ones?`)) {
                                triggerMerge(data.collection);
                            } else {
                                showJobError('Some PDFs failed to generate.');
                            }
                        } else {
                            showJobError(data.collection.error || 'All generations failed.');
                        }
                    }
                }
            }
        } catch (err) {
            console.error('Status poll failed:', err);
        }
    }

    function updateProgress(collection) {
        collectionItems = collection.items;
        
        let completed = 0;
        let totalProgress = 0;
        
        progressSteps.innerHTML = '';
        
        collectionItems.forEach((item, idx) => {
            if (item.status === 'completed') completed++;
            totalProgress += (item.progress || 0);
            
            // Build UI for each item
            let statusIcon = `<div class="step-indicator"></div>`;
            let statusClass = '';
            let statusText = item.message || item.status;
            
            if (item.status === 'completed') {
                statusClass = 'completed';
                statusIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="3" stroke-linecap="round"><path d="M20 6L9 17l-5-5"/></svg>`;
            } else if (item.status === 'failed') {
                statusClass = 'failed';
                statusIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
                statusText = item.error || 'Failed';
            } else if (item.status !== 'queued') {
                statusClass = 'active';
            }
            
            progressSteps.innerHTML += `
                <div class="step ${statusClass}" style="margin-bottom: 8px;">
                    <div style="width: 20px; display: flex; justify-content: center;">${statusIcon}</div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-size: 14px; font-weight: 500; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${idx + 1}. ${item.title || item.url}</div>
                        <div class="step-text" style="font-size: 12px;">${statusText}</div>
                    </div>
                    ${item.status === 'failed' ? `<button onclick="document.dispatchEvent(new CustomEvent('retryUrl', {detail: '${item.id}'}))" style="background: none; border: 1px solid var(--border); color: var(--text-primary); border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 11px;">Retry</button>` : ''}
                </div>
            `;
        });
        
        const avgProgress = Math.floor(totalProgress / collectionItems.length);
        progressBarFill.style.width = avgProgress + '%';
        progressPercent.textContent = avgProgress + '%';
        
        progressTitle.textContent = 'Generating PDFs...';
        progressSubtitle.textContent = `${completed} / ${collectionItems.length} completed`;
    }

    document.addEventListener('retryUrl', async (e) => {
        if (!currentCollectionId) return;
        const itemId = e.detail;
        
        const request = {
            page_size: settingPageSize.value,
            font_size: settingFontSize.value,
            font_family: settingFontFamily.value,
            include_images: settingImages.checked,
            include_links: settingLinks.checked,
            include_toc: settingToc.checked,
            include_code: settingCode.checked,
        };
        
        await fetch(`/api/collections/${currentCollectionId}/retry/${itemId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        startPolling(); // Resume polling
    });

    async function triggerMerge(collection) {
        progressTitle.textContent = 'Merging PDFs...';
        progressSubtitle.textContent = 'Finalizing your document';
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '99%';
        progressSpinner.style.display = 'block';

        const request = {
            title: settingTitle.value.trim() || 'Study Material Collection',
            add_cover_page: settingCover.checked,
            add_source_separator: settingSeparator.checked,
            generate_toc: true
        };

        try {
            const response = await fetch(`/api/collections/${currentCollectionId}/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(request),
            });

            const data = await response.json();
            if (data.success) {
                showCompleted(data.collection);
            } else {
                showJobError(data.error || 'Failed to merge PDFs.');
            }
        } catch (err) {
            showJobError('Network error during merge.');
        }
    }

    function showCompleted(collection) {
        progressSpinner.style.display = 'none';
        progressCheck.style.display = 'block';
        progressTitle.textContent = 'PDF Generated Successfully!';
        progressSubtitle.textContent = '';
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';

        // Setup Download Section
        dlSources.textContent = `${collection.items.filter(i => i.status === 'completed').length} Sources`;
        dlPages.textContent = `${collection.total_pages} Pages`;
        dlSize.textContent = `${collection.final_pdf_size_mb.toFixed(1)} MB`;
        downloadFilename.textContent = collection.final_pdf_filename;
        downloadBtn.href = `/api/collections/${collection.id}/download`;
        
        // Individual Downloads
        individualDownloadsList.innerHTML = '';
        collection.items.forEach((item, idx) => {
            if (item.status === 'completed' && item.filename) {
                individualDownloadsList.innerHTML += `
                    <div class="individual-download-item">
                        <div class="individual-download-info">
                            <div class="individual-download-title">${idx + 1}. ${item.title}</div>
                            <div class="individual-download-url">${item.url}</div>
                        </div>
                        <a href="/api/collections/${collection.id}/urls/${item.id}/download" class="individual-download-btn" download>Download</a>
                    </div>
                `;
            }
        });

        // Initialize Page Management UI
        totalPagesCount = collection.total_pages;
        pageStates = Array(totalPagesCount).fill(true);
        pageSelections = Array(totalPagesCount).fill(false);
        pageRotations = {};
        pageOrder = Array.from({length: totalPagesCount}, (_, i) => i);
        pmRangeInput.value = '';
        pmErrorMessage.textContent = '';
        
        renderThumbnails();
        updatePmUI();
        
        pmSection.style.display = 'block';
        downloadSection.classList.remove('active');
    }
    
    function renderThumbnails() {
        pmThumbnailsGrid.innerHTML = '';
        
        pageOrder.forEach((originalIndex, displayIndex) => {
            const div = document.createElement('div');
            div.className = 'pm-thumbnail-item';
            div.dataset.index = originalIndex;
            div.draggable = true;
            
            const currentRotation = pageRotations[originalIndex] || 0;
            
            div.innerHTML = `
                <div class="pm-thumbnail-img-wrapper" style="transform: rotate(${currentRotation}deg); transition: transform 0.3s ease;">
                    <img class="pm-thumbnail-img" src="/api/collections/${currentCollectionId}/thumbnails/${originalIndex}" loading="lazy" alt="Page ${originalIndex + 1}">
                    <div class="pm-thumbnail-zoom" title="View Full Page" style="transform: rotate(-${currentRotation}deg);">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                    </div>
                    <div class="pm-thumbnail-rotate" title="Rotate Page" style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.6); color: white; border-radius: 4px; padding: 4px; cursor: pointer; transform: rotate(-${currentRotation}deg);">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 2v6h-6"></path><path d="M21 13a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path></svg>
                    </div>
                    <div class="pm-thumbnail-status" style="transform: rotate(-${currentRotation}deg);">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M20 6L9 17l-5-5"/></svg>
                    </div>
                </div>
                <div class="pm-thumbnail-label">Page ${originalIndex + 1}</div>
            `;
            
            div.addEventListener('click', (e) => {
                if (e.target.closest('.pm-thumbnail-zoom')) {
                    e.stopPropagation();
                    openImageModal(originalIndex);
                    return;
                }
                if (e.target.closest('.pm-thumbnail-rotate')) {
                    e.stopPropagation();
                    pageRotations[originalIndex] = (currentRotation + 90) % 360;
                    renderThumbnails();
                    updatePmUI();
                    return;
                }
                pageSelections[originalIndex] = !pageSelections[originalIndex];
                updatePmUI();
            });
            
            div.addEventListener('dblclick', (e) => {
                openImageModal(originalIndex);
            });
            
            // Drag and Drop Logic
            div.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', displayIndex);
                div.classList.add('dragging');
            });
            div.addEventListener('dragend', () => {
                div.classList.remove('dragging');
                document.querySelectorAll('.pm-thumbnail-item').forEach(el => el.classList.remove('drag-over'));
            });
            div.addEventListener('dragover', (e) => {
                e.preventDefault();
                div.classList.add('drag-over');
            });
            div.addEventListener('dragleave', () => {
                div.classList.remove('drag-over');
            });
            div.addEventListener('drop', (e) => {
                e.preventDefault();
                div.classList.remove('drag-over');
                const fromIndex = parseInt(e.dataTransfer.getData('text/plain'));
                const toIndex = displayIndex;
                if (fromIndex !== toIndex) {
                    const item = pageOrder.splice(fromIndex, 1)[0];
                    pageOrder.splice(toIndex, 0, item);
                    renderThumbnails();
                    updatePmUI();
                }
            });
            
            pmThumbnailsGrid.appendChild(div);
        });
    }
    
    function openImageModal(pageIndex) {
        modalImg.style.display = 'none';
        modalLoader.style.display = 'block';
        imageModal.style.display = 'flex';
        
        modalImg.onload = () => {
            modalLoader.style.display = 'none';
            modalImg.style.display = 'block';
        };
        
        modalImg.src = `/api/collections/${currentCollectionId}/thumbnails/${pageIndex}?zoom=2.0`;
    }
    
    function updatePmUI() {
        let kept = 0;
        let removed = 0;
        
        const items = pmThumbnailsGrid.querySelectorAll('.pm-thumbnail-item');
        for (let i = 0; i < totalPagesCount; i++) {
            const originalIndex = pageOrder[i];
            const item = items[i];
            if (!item) continue;
            
            if (pageStates[originalIndex]) {
                kept++;
                item.classList.remove('removed');
                const svg = item.querySelector('.pm-thumbnail-status svg');
                if (svg) svg.innerHTML = '<path d="M20 6L9 17l-5-5"/>';
            } else {
                removed++;
                item.classList.add('removed');
                const svg = item.querySelector('.pm-thumbnail-status svg');
                if (svg) svg.innerHTML = '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>';
            }
            
            if (pageSelections[originalIndex]) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        }
        
        pmTotal.textContent = `Total: ${totalPagesCount}`;
        pmKept.textContent = `Kept: ${kept}`;
        pmRemoved.textContent = `Removed: ${removed}`;
    }
    
    function applyCustomRange() {
        const val = pmRangeInput.value.trim();
        pmErrorMessage.textContent = '';
        if (!val) {
            pmErrorMessage.textContent = 'Please enter a valid range (e.g. 1-5, 8).';
            return;
        }
        
        let newStates = Array(totalPagesCount).fill(false);
        const parts = val.split(',');
        
        for (let part of parts) {
            part = part.trim();
            if (!part) continue;
            
            if (part.includes('-')) {
                const rangeParts = part.split('-');
                if (rangeParts.length !== 2) {
                    pmErrorMessage.textContent = `Invalid range format: ${part}`;
                    return;
                }
                const start = parseInt(rangeParts[0].trim());
                const end = parseInt(rangeParts[1].trim());
                
                if (isNaN(start) || isNaN(end) || start < 1 || start > end) {
                    pmErrorMessage.textContent = `Invalid numeric range: ${part}`;
                    return;
                }
                for (let i = start; i <= end; i++) {
                    if (i > 0 && i <= totalPagesCount) newStates[i - 1] = true;
                }
            } else {
                const num = parseInt(part);
                if (isNaN(num) || num < 1) {
                    pmErrorMessage.textContent = `Invalid page number: ${part}`;
                    return;
                }
                if (num > 0 && num <= totalPagesCount) newStates[num - 1] = true;
            }
        }
        
        pageStates = newStates;
        pageSelections.fill(false);
        updatePmUI();
    }
    
    async function applyPageEdits() {
        const keepPages = [];
        for (let i = 0; i < totalPagesCount; i++) {
            const originalIndex = pageOrder[i];
            if (pageStates[originalIndex]) keepPages.push(originalIndex);
        }
        
        if (keepPages.length === 0) {
            pmErrorMessage.textContent = 'Cannot apply: You must keep at least one page.';
            return;
        }
        
        pmBtnPreview.disabled = true;
        pmBtnPreview.querySelector('.btn-text').textContent = 'Applying...';
        
        // Filter rotations to only include kept pages that have non-zero rotation
        let validRotations = {};
        for (let key in pageRotations) {
            if (pageRotations[key] > 0 && keepPages.includes(parseInt(key))) {
                validRotations[key] = pageRotations[key];
            }
        }
        
        try {
            const res = await fetch(`/api/collections/${currentCollectionId}/edit-pages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    keep_pages: keepPages,
                    rotations: validRotations 
                })
            });
            const data = await res.json();
            
            if (data.success && data.collection) {
                const col = data.collection;
                const finalSize = col.edited_size_mb || col.final_pdf_size_mb;
                const finalPages = col.edited_total_pages || col.total_pages;
                
                dlPages.textContent = `${finalPages} Pages`;
                dlSize.textContent = `${finalSize.toFixed(1)} MB`;
                
                pmSection.style.display = 'none';
                downloadSection.classList.add('active');
            } else {
                pmErrorMessage.textContent = data.error || 'Failed to edit PDF pages.';
            }
        } catch (e) {
            pmErrorMessage.textContent = 'Network error while applying edits.';
        } finally {
            pmBtnPreview.disabled = false;
            pmBtnPreview.querySelector('.btn-text').textContent = 'Apply Changes & Preview';
        }
    }

    function showJobError(msg) {
        progressSpinner.style.display = 'none';
        progressTitle.textContent = 'Generation Failed';
        progressSubtitle.textContent = '';
        errorDetail.textContent = msg;
        errorSection.classList.add('active');
    }

    function resetToHome() {
        stopPolling();
        currentCollectionId = null;
        collectionItems = [];
        urlList.innerHTML = '';
        urlListContainer.style.display = 'none';

        progressSection.classList.remove('active');
        pmSection.style.display = 'none';
        downloadSection.classList.remove('active');
        errorSection.classList.remove('active');

        heroSection.style.display = '';
        document.querySelector('.how-it-works').style.display = '';
        document.querySelector('.features').style.display = '';
        document.querySelector('.about').style.display = '';
        
        settingTitle.value = '';

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ── Smooth Scroll for Nav Links ─────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const navbar = document.getElementById('navbar');
        const scrollTop = window.pageYOffset;
        if (scrollTop > 50) {
            navbar.style.background = 'rgba(10, 10, 15, 0.95)';
        } else {
            navbar.style.background = 'rgba(10, 10, 15, 0.8)';
        }
        lastScroll = scrollTop;
    });

})();
