/**
 * Page2PDF Studio — Frontend
 * Sources → Build → Edit pages → Export.
 * All user/remote text is rendered with textContent or escaped; no inline handlers.
 */
(function () {
    'use strict';

    // ── Helpers ─────────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
    const icon = (name, cls = '') => `<svg class="i ${cls}"><use href="#i-${name}"/></svg>`;
    const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
    const formatMb = (mb) => (mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(mb * 1024))} KB`);
    const storage = {
        get(key, fallback) {
            try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
        },
        set(key, value) {
            try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ }
        },
    };

    class SessionExpiredError extends Error {}

    async function api(path, { method = 'GET', json, form } = {}) {
        const init = { method };
        if (json !== undefined) {
            init.headers = { 'Content-Type': 'application/json' };
            init.body = JSON.stringify(json);
        } else if (form) {
            init.body = form;
        }
        let res;
        try {
            res = await fetch(path, init);
        } catch (e) {
            throw new Error('Network error — check your connection and try again.');
        }
        if (res.status === 404 && path.startsWith('/api/collections/')) {
            throw new SessionExpiredError('This session has expired (the server may have restarted). Please start a new collection.');
        }
        let data = null;
        try { data = await res.json(); } catch (e) { /* non-JSON */ }
        if (!res.ok) {
            const detail = data && (data.error || (typeof data.detail === 'string' ? data.detail : null));
            throw new Error(detail || `Request failed (${res.status}).`);
        }
        if (data && data.success === false) throw new Error(data.error || 'Something went wrong.');
        return data;
    }

    function setLoading(button, loading, label) {
        if (!button) return;
        button.disabled = loading;
        button.classList.toggle('is-loading', loading);
        const text = button.querySelector('.btn-text');
        if (text && label !== undefined) text.textContent = label;
    }

    // ── Toasts ──────────────────────────────────────────────────
    const toastStack = $('toast-stack');
    function toast(message, type = 'info', { action, onAction, duration = 4200 } = {}) {
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.setAttribute('role', type === 'error' ? 'alert' : 'status');
        const iconName = type === 'success' ? 'check' : type === 'error' ? 'alert' : 'alert';
        el.innerHTML = `${icon(iconName)}<span></span>`;
        el.querySelector('span').textContent = message;
        if (action) {
            const btn = document.createElement('button');
            btn.className = 'toast-action';
            btn.type = 'button';
            btn.textContent = action;
            btn.addEventListener('click', () => { onAction && onAction(); dismiss(); });
            el.appendChild(btn);
        }
        toastStack.appendChild(el);
        let timer = setTimeout(dismiss, duration);
        el.addEventListener('mouseenter', () => clearTimeout(timer));
        el.addEventListener('mouseleave', () => { timer = setTimeout(dismiss, 1800); });
        function dismiss() {
            if (!el.isConnected) return;
            el.classList.add('leaving');
            setTimeout(() => el.remove(), 250);
        }
        while (toastStack.children.length > 3) toastStack.firstElementChild.remove();
    }

    // ── Modals ──────────────────────────────────────────────────
    const openModals = [];
    function openModal(el) {
        el.hidden = false;
        openModals.push({ el, returnFocus: document.activeElement });
        const focusable = el.querySelector('input:not([hidden]), textarea:not([hidden]), button:not([data-close-modal])');
        setTimeout(() => focusable && focusable.focus(), 30);
    }
    function closeModal(el) {
        const idx = openModals.findIndex((m) => m.el === el);
        if (idx === -1) return;
        const [entry] = openModals.splice(idx, 1);
        el.hidden = true;
        if (el.onclose) el.onclose();
        if (entry.returnFocus && entry.returnFocus.focus) entry.returnFocus.focus();
    }
    function closeTopModal() {
        const top = openModals[openModals.length - 1];
        if (top) closeModal(top.el);
        return Boolean(top);
    }
    document.querySelectorAll('.modal, .lightbox').forEach((modal) => {
        modal.addEventListener('mousedown', (e) => { if (e.target === modal) closeModal(modal); });
        modal.querySelectorAll('[data-close-modal]').forEach((btn) => btn.addEventListener('click', () => closeModal(modal)));
    });

    function confirmDialog({ title, body, ok = 'Continue', cancel = 'Cancel' }) {
        const modal = $('confirm-modal');
        $('confirm-title').textContent = title;
        $('confirm-body').textContent = body;
        $('confirm-ok').textContent = ok;
        $('confirm-cancel').textContent = cancel;
        return new Promise((resolve) => {
            let result = false;
            const okBtn = $('confirm-ok');
            const cancelBtn = $('confirm-cancel');
            const onOk = () => { result = true; closeModal(modal); };
            const onCancel = () => closeModal(modal);
            okBtn.addEventListener('click', onOk, { once: true });
            cancelBtn.addEventListener('click', onCancel, { once: true });
            modal.onclose = () => {
                okBtn.removeEventListener('click', onOk);
                cancelBtn.removeEventListener('click', onCancel);
                modal.onclose = null;
                resolve(result);
            };
            openModal(modal);
            setTimeout(() => okBtn.focus(), 40);
        });
    }

    // ── Theme ───────────────────────────────────────────────────
    $('theme-toggle').addEventListener('click', () => {
        const root = document.documentElement;
        const current = root.dataset.theme
            || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
        const next = current === 'light' ? 'dark' : 'light';
        root.dataset.theme = next;
        try { localStorage.setItem('p2p-theme', next); } catch (e) { /* ignore */ }
    });

    // ── Navigation ──────────────────────────────────────────────
    const navbar = $('navbar');
    const navLinks = $('nav-links');
    const navToggle = $('nav-toggle');
    navToggle.addEventListener('click', () => {
        const open = navLinks.classList.toggle('open');
        navToggle.setAttribute('aria-expanded', String(open));
    });
    navLinks.querySelectorAll('a').forEach((link) => link.addEventListener('click', (e) => {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
        if (document.body.classList.contains('is-working')) {
            // The landing sections are hidden while working; jump back to the workspace instead.
            e.preventDefault();
            $('workspace').scrollIntoView({ behavior: 'smooth' });
        }
    }));
    // Scroll reveal for the landing sections
    const revealTargets = document.querySelectorAll('[data-reveal]');
    if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('is-visible');
                io.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
        revealTargets.forEach((el) => io.observe(el));
    } else {
        revealTargets.forEach((el) => el.classList.add('is-visible'));
    }

    $('cta-start-btn').addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => $('url-input').focus({ preventScroll: true }), 450);
    });

    const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 12);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // ── Settings (persisted) ────────────────────────────────────
    const settings = {
        title: $('setting-title'),
        author: $('setting-author'),
        pageSize: $('setting-page-size'),
        fontSize: $('setting-font-size'),
        fontFamily: $('setting-font-family'),
        images: $('setting-images'),
        links: $('setting-links'),
        toc: $('setting-toc'),
        code: $('setting-code'),
        cover: $('setting-cover'),
        separator: $('setting-separator'),
    };
    const PERSISTED = ['author', 'pageSize', 'fontSize', 'fontFamily', 'images', 'links', 'toc', 'code', 'cover', 'separator'];
    (function restoreSettings() {
        const saved = storage.get('p2p-settings', {});
        PERSISTED.forEach((key) => {
            if (!(key in saved)) return;
            const el = settings[key];
            if (el.type === 'checkbox') el.checked = Boolean(saved[key]);
            else el.value = saved[key];
        });
    })();
    function saveSettings() {
        const out = {};
        PERSISTED.forEach((key) => {
            const el = settings[key];
            out[key] = el.type === 'checkbox' ? el.checked : el.value;
        });
        storage.set('p2p-settings', out);
    }
    PERSISTED.forEach((key) => settings[key].addEventListener('change', saveSettings));
    settings.author.addEventListener('input', saveSettings);

    const settingsToggle = $('settings-toggle');
    const settingsPanel = $('settings-panel');
    settingsToggle.addEventListener('click', () => {
        const open = settingsPanel.classList.toggle('open');
        settingsToggle.setAttribute('aria-expanded', String(open));
    });

    function generationOptions() {
        return {
            page_size: settings.pageSize.value,
            font_size: settings.fontSize.value,
            font_family: settings.fontFamily.value,
            include_images: settings.images.checked,
            include_links: settings.links.checked,
            include_toc: settings.toc.checked,
            include_code: settings.code.checked,
        };
    }
    const documentTitle = () => settings.title.value.trim() || 'Study Material Collection';

    // ── State ───────────────────────────────────────────────────
    let collectionId = null;
    let collection = null;
    let items = [];          // server items
    let pending = [];        // client-side placeholders while adding/uploading
    let pollTimer = null;
    let thumbVersion = Date.now();

    // ── Sources ─────────────────────────────────────────────────
    const urlInput = $('url-input');
    const addUrlBtn = $('add-url-btn');
    const errorMessage = $('error-message');
    const sourceListWrap = $('url-list-container');
    const sourceList = $('url-list');
    const sourceCount = $('source-count');
    const buildBtn = $('generate-all-btn');
    const composer = $('composer');
    const fileInput = $('pdf-upload-input');
    const uploadBtn = $('upload-pdf-btn');
    const SUPPORTED_FILE = /\.(pdf|png|jpe?g|webp)$/i;
    const URL_PATTERN = /\bhttps?:\/\/[^\s<>"'`]+/gi;

    const showError = (msg) => { errorMessage.textContent = msg || ''; };

    function normalizeUrl(url) {
        url = url.trim().replace(/[),.;]+$/, '');
        if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
        return url;
    }

    function parseUrls(text) {
        const found = text.match(URL_PATTERN);
        if (found && found.length) return [...new Set(found.map(normalizeUrl))];
        const parts = text.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
        return [...new Set(parts.map(normalizeUrl))];
    }

    async function ensureCollection() {
        if (collectionId) return;
        const data = await api('/api/collections', { method: 'POST', json: { title: documentTitle() } });
        collectionId = data.collection.id;
        collection = data.collection;
    }

    function syncFromServer(col) {
        collection = col;
        items = col.items;
        renderSources();
    }

    async function addUrls(urls) {
        if (!urls.length) return;
        showError('');
        try {
            await ensureCollection();
        } catch (e) {
            showError(e.message);
            return;
        }
        let added = 0;
        const failures = [];
        for (const url of urls) {
            const temp = { id: 'tmp_' + Math.random().toString(36).slice(2), url, title: 'Fetching page title…', pending: true };
            pending.push(temp);
            renderSources();
            try {
                const data = await api(`/api/collections/${collectionId}/urls`, { method: 'POST', json: { url } });
                pending = pending.filter((p) => p !== temp);
                syncFromServer(data.collection);
                added++;
            } catch (e) {
                pending = pending.filter((p) => p !== temp);
                renderSources();
                if (e instanceof SessionExpiredError) { resetAll(); toast(e.message, 'error'); return; }
                failures.push(`${url}: ${e.message}`);
            }
        }
        if (failures.length === 1 && urls.length === 1) showError(failures[0].split(': ').slice(1).join(': '));
        else if (failures.length) showError(`${failures.length} link(s) could not be added. ${failures[0]}`);
        if (added > 1) toast(`Added ${added} links`, 'success');
    }

    async function addFromInput() {
        const raw = urlInput.value.trim();
        if (!raw) {
            showError('Paste a webpage link first.');
            urlInput.focus();
            return;
        }
        const urls = parseUrls(raw);
        urlInput.value = '';
        addUrlBtn.disabled = true;
        await addUrls(urls);
        addUrlBtn.disabled = false;
        urlInput.focus();
    }

    async function uploadFiles(files) {
        const valid = files.filter((f) => SUPPORTED_FILE.test(f.name));
        if (valid.length !== files.length) {
            showError('Only PDF, PNG, JPG and WEBP files are supported.');
            if (!valid.length) return;
        } else {
            showError('');
        }
        try {
            await ensureCollection();
        } catch (e) {
            showError(e.message);
            return;
        }
        for (const file of valid) {
            const temp = { id: 'tmp_' + Math.random().toString(36).slice(2), url: `local://${file.name}`, title: file.name, pending: true, uploading: true };
            pending.push(temp);
            renderSources();
            const form = new FormData();
            form.append('file', file);
            try {
                const data = await api(`/api/collections/${collectionId}/upload`, { method: 'POST', form });
                pending = pending.filter((p) => p !== temp);
                syncFromServer(data.collection);
            } catch (e) {
                pending = pending.filter((p) => p !== temp);
                renderSources();
                if (e instanceof SessionExpiredError) { resetAll(); toast(e.message, 'error'); return; }
                showError(`${file.name}: ${e.message}`);
            }
        }
    }

    async function removeSource(id) {
        const removed = items.find((i) => i.id === id);
        try {
            const data = await api(`/api/collections/${collectionId}/urls/${encodeURIComponent(id)}`, { method: 'DELETE' });
            syncFromServer(data.collection);
            if (removed && !removed.url.startsWith('local://')) {
                toast('Source removed', 'info', { action: 'Undo', onAction: () => addUrls([removed.url]) });
            } else {
                toast('Source removed');
            }
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function saveOrder() {
        if (!collectionId) return;
        try {
            const data = await api(`/api/collections/${collectionId}/urls/reorder`, {
                method: 'PATCH', json: { item_ids: items.map((i) => i.id) },
            });
            collection = data.collection;
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    function moveSource(id, delta) {
        const from = items.findIndex((i) => i.id === id);
        const to = from + delta;
        if (from < 0 || to < 0 || to >= items.length) return;
        const [it] = items.splice(from, 1);
        items.splice(to, 0, it);
        renderSources();
        saveOrder();
    }

    function sourceKind(item) {
        if (!item.url.startsWith('local://')) return 'web';
        return /\.pdf$/i.test(item.title || item.url) ? 'pdf' : 'image';
    }

    function sourceMeta(item) {
        if (item.status === 'failed' && item.error) return item.error;
        if (item.uploading) return 'Uploading…';
        if (sourceKind(item) !== 'web') return sourceKind(item) === 'pdf' ? 'PDF file' : 'Image';
        try {
            const u = new URL(item.url);
            return u.hostname.replace(/^www\./, '') + (u.pathname !== '/' ? u.pathname : '');
        } catch (e) {
            return item.url;
        }
    }

    function avatarLetter(item) {
        const kind = sourceKind(item);
        if (kind === 'pdf') return 'PDF';
        if (kind === 'image') return 'IMG';
        try { return new URL(item.url).hostname.replace(/^www\./, '').charAt(0); } catch (e) { return '?'; }
    }

    function renderSources() {
        const all = [...items, ...pending];
        sourceListWrap.hidden = all.length === 0;
        sourceCount.textContent = plural(all.length, 'source');
        buildBtn.disabled = items.length === 0 || pending.length > 0;
        buildBtn.querySelector('.btn-text').textContent = items.length > 1 ? `Build PDF from ${items.length} sources` : 'Build PDF';

        sourceList.innerHTML = all.map((item, index) => {
            const kind = sourceKind(item);
            const avatar = avatarLetter(item);
            const isPending = Boolean(item.pending);
            const failed = item.status === 'failed';
            return `
                <li class="source-item${isPending ? ' is-pending' : ''}" data-id="${escapeHtml(item.id)}" ${isPending ? '' : 'draggable="true"'}>
                    <span class="source-grip" title="Drag to reorder">${icon('grip')}</span>
                    <span class="source-avatar" data-kind="${kind}" style="${avatar.length > 1 ? 'font-size:9px' : ''}">${escapeHtml(avatar)}</span>
                    <div class="source-body">
                        <div class="source-title">${escapeHtml(item.title || 'Untitled document')}</div>
                        <div class="source-meta"${failed ? ' style="color:var(--danger)"' : ''}>${escapeHtml(sourceMeta(item))}</div>
                    </div>
                    ${isPending ? '<span class="spinner" style="color:var(--accent-text);margin-right:8px"></span>' : `
                    <div class="source-actions">
                        <button class="icon-btn" type="button" data-action="up" aria-label="Move up" ${index === 0 ? 'disabled' : ''}>${icon('up')}</button>
                        <button class="icon-btn" type="button" data-action="down" aria-label="Move down" ${index >= items.length - 1 ? 'disabled' : ''}>${icon('down')}</button>
                        <button class="icon-btn danger" type="button" data-action="remove" aria-label="Remove">${icon('trash')}</button>
                    </div>`}
                </li>`;
        }).join('');
    }

    sourceList.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const id = btn.closest('.source-item').dataset.id;
        if (btn.dataset.action === 'up') moveSource(id, -1);
        else if (btn.dataset.action === 'down') moveSource(id, 1);
        else if (btn.dataset.action === 'remove') removeSource(id);
    });

    // Drag-reorder sources
    let draggingSourceId = null;
    sourceList.addEventListener('dragstart', (e) => {
        const li = e.target.closest('.source-item');
        if (!li) return;
        draggingSourceId = li.dataset.id;
        li.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('application/x-p2p-source', draggingSourceId);
    });
    sourceList.addEventListener('dragover', (e) => {
        if (!draggingSourceId) return;
        e.preventDefault();
        e.stopPropagation();
        sourceList.querySelectorAll('.drop-target').forEach((el) => el.classList.remove('drop-target'));
        const li = e.target.closest('.source-item');
        if (li && li.dataset.id !== draggingSourceId) li.classList.add('drop-target');
    });
    sourceList.addEventListener('drop', (e) => {
        if (!draggingSourceId) return;
        e.preventDefault();
        e.stopPropagation();
        const li = e.target.closest('.source-item');
        if (li && li.dataset.id !== draggingSourceId) {
            const from = items.findIndex((i) => i.id === draggingSourceId);
            const to = items.findIndex((i) => i.id === li.dataset.id);
            if (from > -1 && to > -1) {
                const [it] = items.splice(from, 1);
                items.splice(to, 0, it);
                renderSources();
                saveOrder();
            }
        }
    });
    sourceList.addEventListener('dragend', () => {
        draggingSourceId = null;
        sourceList.querySelectorAll('.dragging, .drop-target').forEach((el) => el.classList.remove('dragging', 'drop-target'));
    });

    $('clear-sources-btn').addEventListener('click', async () => {
        if (!items.length) return;
        const ok = await confirmDialog({ title: 'Clear all sources?', body: `This removes ${plural(items.length, 'source')} from the list.`, ok: 'Clear all' });
        if (ok) resetAll();
    });

    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addFromInput(); }
    });
    urlInput.addEventListener('input', () => showError(''));
    urlInput.addEventListener('paste', (e) => {
        const text = (e.clipboardData || window.clipboardData).getData('text');
        const urls = text.match(URL_PATTERN) || [];
        if (urls.length > 1) {
            e.preventDefault();
            addUrls([...new Set(urls.map(normalizeUrl))]);
        }
    });
    addUrlBtn.addEventListener('click', addFromInput);
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async () => {
        const files = Array.from(fileInput.files || []);
        fileInput.value = '';
        await uploadFiles(files);
    });

    // Drop anywhere on the composer card
    let dragDepth = 0;
    const isExternalDrag = (e) => !draggingSourceId && e.dataTransfer && Array.from(e.dataTransfer.types || []).some((t) => t === 'Files' || t === 'text/uri-list' || t === 'text/plain');
    composer.addEventListener('dragenter', (e) => {
        if (!isExternalDrag(e)) return;
        e.preventDefault();
        dragDepth++;
        composer.classList.add('drag-active');
    });
    composer.addEventListener('dragover', (e) => { if (isExternalDrag(e)) e.preventDefault(); });
    composer.addEventListener('dragleave', () => {
        dragDepth = Math.max(0, dragDepth - 1);
        if (!dragDepth) composer.classList.remove('drag-active');
    });
    composer.addEventListener('drop', async (e) => {
        if (!isExternalDrag(e)) return;
        e.preventDefault();
        dragDepth = 0;
        composer.classList.remove('drag-active');
        const files = Array.from(e.dataTransfer.files || []);
        if (files.length) { await uploadFiles(files); return; }
        const text = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain');
        const urls = (text.match(URL_PATTERN) || []).map(normalizeUrl);
        if (urls.length) await addUrls([...new Set(urls)]);
    });

    document.querySelectorAll('.chip[data-url]').forEach((chip) => chip.addEventListener('click', () => {
        urlInput.value = chip.dataset.url;
        urlInput.focus();
        showError('');
    }));

    // ── Workspace / stepper ─────────────────────────────────────
    const workspace = $('workspace');
    const progressPanel = $('progress-panel');
    const errorPanel = $('error-section');
    const editorPanel = $('page-management-section');
    const exportPanel = $('download-section');
    const STEP_ORDER = ['build', 'edit', 'export'];

    function showPanel(panel, step) {
        document.body.classList.add('is-working');
        workspace.hidden = false;
        [progressPanel, errorPanel, editorPanel, exportPanel].forEach((p) => { p.hidden = p !== panel; });
        const current = STEP_ORDER.indexOf(step);
        document.querySelectorAll('.stepper-step').forEach((li) => {
            const i = STEP_ORDER.indexOf(li.dataset.step);
            li.classList.toggle('is-current', i === current);
            li.classList.toggle('is-done', i < current);
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function backToSources() {
        stopPolling();
        document.body.classList.remove('is-working');
        workspace.hidden = true;
        renderSources();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function resetAll() {
        stopPolling();
        collectionId = null;
        collection = null;
        items = [];
        pending = [];
        settings.title.value = '';
        showError('');
        editor.reset();
        resetExportOptions();
        backToSources();
    }

    // ── Build (generate + merge) ────────────────────────────────
    const progressRing = $('progress-ring');
    const ringFill = $('ring-fill');
    const RING = 2 * Math.PI * 28;
    const progressTitle = $('progress-title');
    const progressSubtitle = $('progress-subtitle');
    const progressPercent = $('progress-percent');
    const progressSteps = $('progress-steps');
    const progressActions = $('progress-actions');

    function setRing(pct, done = false) {
        ringFill.style.strokeDashoffset = String(RING * (1 - pct / 100));
        progressPercent.textContent = `${Math.round(pct)}%`;
        progressRing.classList.toggle('is-done', done);
    }

    async function startBuild() {
        if (!collectionId || !items.length) return;
        showPanel(progressPanel, 'build');
        progressActions.hidden = true;
        progressTitle.textContent = 'Building your PDF…';
        progressSubtitle.textContent = `Processing ${plural(items.length, 'source')}`;
        setRing(0);
        renderProgress(items);
        try {
            await api(`/api/collections/${collectionId}/generate`, { method: 'POST', json: generationOptions() });
            startPolling();
        } catch (e) {
            showFatal(e.message);
        }
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(pollStatus, 900);
        pollStatus();
    }
    function stopPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
    }

    let polling = false;
    async function pollStatus() {
        if (!collectionId || polling) return;
        polling = true;
        try {
            const data = await api(`/api/collections/${collectionId}/status`);
            const col = data.collection;
            collection = col;
            items = col.items;
            const done = items.filter((i) => i.status === 'completed').length;
            const failed = items.filter((i) => i.status === 'failed').length;
            const avg = items.reduce((sum, i) => sum + (i.progress || 0), 0) / Math.max(1, items.length);
            renderProgress(items);
            setRing(Math.min(avg, 96));
            progressSubtitle.textContent = `${done} of ${items.length} ready${failed ? ` · ${failed} failed` : ''}`;

            const finished = items.every((i) => i.status === 'completed' || i.status === 'failed');
            if (finished && (col.status === 'completed' || col.status === 'failed')) {
                stopPolling();
                if (!failed) {
                    await mergeCollection();
                } else if (done > 0) {
                    progressTitle.textContent = `${plural(failed, 'source')} couldn't be converted`;
                    progressSubtitle.textContent = 'Retry them, or continue without them.';
                    progressActions.hidden = false;
                } else {
                    showFatal(items.find((i) => i.error)?.error || 'None of the sources could be converted.');
                }
            }
        } catch (e) {
            stopPolling();
            showFatal(e.message);
        } finally {
            polling = false;
        }
    }

    const STATUS_LABEL = {
        queued: 'Waiting…', validating: 'Validating link…', fetching: 'Fetching page…', extracting: 'Extracting content…',
        cleaning: 'Cleaning up…', formatting: 'Formatting…', generating_pdf: 'Rendering PDF…', completed: 'Ready', failed: 'Failed',
    };

    function renderProgress(list) {
        progressSteps.innerHTML = list.map((item, idx) => {
            const state = item.status === 'completed' ? 'is-done' : item.status === 'failed' ? 'is-failed' : item.status === 'queued' ? '' : 'is-active';
            const statusIcon = item.status === 'completed' ? icon('check', 'i-sm')
                : item.status === 'failed' ? icon('x', 'i-sm')
                : item.status === 'queued' ? `<span style="font-size:11px;font-weight:700">${idx + 1}</span>`
                : '<span class="spinner" style="width:13px;height:13px"></span>';
            const msg = item.status === 'failed' ? (item.error || 'Failed') : (item.message || STATUS_LABEL[item.status] || item.status);
            return `
                <li class="progress-item ${state}">
                    <span class="progress-status">${statusIcon}</span>
                    <div class="progress-body">
                        <div class="progress-name">${escapeHtml(item.title || item.url)}</div>
                        <div class="progress-msg">${escapeHtml(msg)}</div>
                        ${state === 'is-active' ? `<div class="mini-bar"><span style="width:${Number(item.progress) || 0}%"></span></div>` : ''}
                    </div>
                    ${item.status === 'failed' ? `<button class="btn btn-ghost" type="button" data-retry="${escapeHtml(item.id)}">${icon('refresh', 'i-sm')}Retry</button>` : ''}
                </li>`;
        }).join('');
    }

    progressSteps.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-retry]');
        if (!btn || !collectionId) return;
        btn.disabled = true;
        progressActions.hidden = true;
        progressTitle.textContent = 'Retrying…';
        try {
            await api(`/api/collections/${collectionId}/retry/${encodeURIComponent(btn.dataset.retry)}`, { method: 'POST', json: generationOptions() });
            startPolling();
        } catch (err) {
            toast(err.message, 'error');
            btn.disabled = false;
        }
    });

    $('progress-merge-btn').addEventListener('click', () => mergeCollection());
    $('progress-back-btn').addEventListener('click', backToSources);
    $('retry-btn').addEventListener('click', () => {
        if (collectionId) backToSources(); else resetAll();
    });
    buildBtn.addEventListener('click', startBuild);

    async function mergeCollection() {
        progressActions.hidden = true;
        progressTitle.textContent = 'Merging everything together…';
        progressSubtitle.textContent = 'Adding contents, cover and bookmarks';
        setRing(98);
        try {
            const data = await api(`/api/collections/${collectionId}/merge`, {
                method: 'POST',
                json: {
                    title: documentTitle(),
                    author: settings.author.value.trim() || null,
                    add_cover_page: settings.cover.checked,
                    add_source_separator: settings.separator.checked,
                    generate_toc: settings.toc.checked,
                },
            });
            setRing(100, true);
            progressTitle.textContent = 'Done!';
            collection = data.collection;
            resetExportOptions();
            setTimeout(() => {
                editor.load(collection);
                showPanel(editorPanel, 'edit');
            }, 350);
        } catch (e) {
            showFatal(e.message);
        }
    }

    function showFatal(message) {
        $('error-detail').textContent = message;
        showPanel(errorPanel, 'build');
    }

    // ── Page editor ─────────────────────────────────────────────
    const editor = (() => {
        const grid = $('pm-thumbnails-grid');
        const pills = { total: $('pm-total'), kept: $('pm-kept'), removed: $('pm-removed'), selected: $('pm-selected') };
        const errorEl = $('pm-error-message');
        const dirtyNote = $('pm-dirty-note');
        const undoBtn = $('pm-undo');
        const redoBtn = $('pm-redo');
        const rangeInput = $('pm-range-input');
        const zoom = $('pm-zoom');

        let pages = [];          // [{ key, src, rot, removed }]
        let selected = new Set();
        let anchorKey = null;
        let undoStack = [];
        let redoStack = [];
        let total = 0;
        let nextKey = 0;
        const nodes = new Map(); // key -> element

        const snapshot = () => JSON.stringify(pages);
        function record() {
            undoStack.push(snapshot());
            if (undoStack.length > 100) undoStack.shift();
            redoStack = [];
        }
        function restore(state) {
            pages = JSON.parse(state);
            const keys = new Set(pages.map((p) => p.key));
            selected = new Set([...selected].filter((k) => keys.has(k)));
            render();
        }

        function load(col) {
            total = col.edited_total_pages || col.total_pages || 0;
            thumbVersion = Date.now();
            nodes.clear();
            grid.innerHTML = '';
            pages = Array.from({ length: total }, (_, i) => ({ key: nextKey++, src: i, rot: 0, removed: false }));
            selected = new Set();
            anchorKey = null;
            undoStack = [];
            redoStack = [];
            errorEl.textContent = '';
            rangeInput.value = '';
            render();
        }

        function reset() {
            pages = [];
            total = 0;
            nodes.clear();
            grid.innerHTML = '';
        }

        const isDirty = () => pages.length !== total || pages.some((p, i) => p.src !== i || p.rot % 360 || p.removed);
        const kept = () => pages.filter((p) => !p.removed);

        function thumbUrl(src, z) {
            return `/api/collections/${collectionId}/thumbnails/${src}?v=${thumbVersion}${z ? `&zoom=${z}` : ''}`;
        }

        function buildNode(page) {
            const el = document.createElement('div');
            el.className = 'thumb';
            el.draggable = true;
            el.tabIndex = 0;
            el.dataset.key = page.key;
            el.innerHTML = `
                <div class="thumb-paper">
                    <span class="thumb-check">${icon('check')}</span>
                    <span class="thumb-badge" hidden></span>
                    <span class="spinner thumb-loading"></span>
                    <img class="thumb-img" alt="" loading="lazy" draggable="false">
                    <div class="thumb-tools">
                        <button class="thumb-tool" type="button" data-tool="zoom" aria-label="Preview page" title="Preview">${icon('zoom')}</button>
                        <button class="thumb-tool" type="button" data-tool="rotate" aria-label="Rotate page" title="Rotate">${icon('rotate')}</button>
                        <button class="thumb-tool danger" type="button" data-tool="remove" aria-label="Remove page" title="Remove / restore">${icon('trash')}</button>
                    </div>
                </div>
                <div class="thumb-label"></div>`;
            const img = el.querySelector('img');
            img.addEventListener('load', () => el.querySelector('.thumb-loading').remove(), { once: true });
            img.addEventListener('error', () => el.querySelector('.thumb-loading')?.remove(), { once: true });
            img.src = thumbUrl(page.src);
            return el;
        }

        function render() {
            const order = [];
            const keysNow = new Set();
            let position = 0;
            pages.forEach((page) => {
                keysNow.add(page.key);
                let el = nodes.get(page.key);
                if (!el) { el = buildNode(page); nodes.set(page.key, el); }
                if (!page.removed) position++;
                const rot = ((page.rot % 360) + 360) % 360;
                const img = el.querySelector('.thumb-img');
                img.style.transform = rot ? `rotate(${rot}deg)${rot % 180 ? ' scale(0.707)' : ''}` : '';
                img.alt = `Page ${page.src + 1}`;
                el.classList.toggle('is-selected', selected.has(page.key));
                el.classList.toggle('is-removed', page.removed);
                el.setAttribute('aria-selected', String(selected.has(page.key)));
                const label = el.querySelector('.thumb-label');
                const origin = page.src + 1;
                label.innerHTML = page.removed
                    ? `<span>Removed</span><small>p.${origin}</small>`
                    : `<span>${position}</span>${position !== origin ? `<small>was p.${origin}</small>` : ''}`;
                const badge = el.querySelector('.thumb-badge');
                badge.hidden = !rot;
                badge.textContent = rot ? `${rot}°` : '';
                order.push(el);
            });
            nodes.forEach((el, key) => { if (!keysNow.has(key)) { el.remove(); nodes.delete(key); } });
            order.forEach((el) => grid.appendChild(el));

            const keptCount = kept().length;
            pills.total.textContent = plural(pages.length, 'page');
            pills.kept.textContent = `${keptCount} kept`;
            pills.removed.textContent = `${pages.length - keptCount} removed`;
            pills.removed.hidden = keptCount === pages.length;
            pills.selected.textContent = `${selected.size} selected`;
            pills.selected.hidden = selected.size === 0;
            dirtyNote.hidden = !isDirty();
            undoBtn.disabled = !undoStack.length;
            redoBtn.disabled = !redoStack.length;
            ['pm-btn-remove-selected', 'pm-btn-keep-selected', 'pm-btn-rotate-selected', 'pm-btn-duplicate'].forEach((id) => { $(id).disabled = selected.size === 0; });
            $('pm-btn-select-all').textContent = selected.size === pages.length && pages.length ? 'Select none' : 'Select all';
            const continueText = $('pm-btn-continue').querySelector('.btn-text');
            continueText.textContent = isDirty() ? 'Apply & continue' : 'Continue to export';
        }

        // Mutations
        function mutate(fn) {
            record();
            fn();
            errorEl.textContent = '';
            render();
        }
        function toggleSelectAll() {
            selected = selected.size === pages.length ? new Set() : new Set(pages.map((p) => p.key));
            render();
        }
        function removeSelected() {
            if (!selected.size) return;
            const targets = pages.filter((p) => selected.has(p.key));
            const restore = targets.every((p) => p.removed);
            mutate(() => { targets.forEach((p) => { p.removed = !restore; }); selected.clear(); });
        }
        function keepSelected() {
            if (!selected.size) return;
            mutate(() => { pages.forEach((p) => { p.removed = !selected.has(p.key); }); selected.clear(); });
        }
        function rotateSelected() {
            if (!selected.size) return;
            mutate(() => pages.forEach((p) => { if (selected.has(p.key)) p.rot = (p.rot + 90) % 360; }));
        }
        function duplicateSelected() {
            if (!selected.size) return;
            mutate(() => {
                const out = [];
                const copies = new Set();
                pages.forEach((p) => {
                    out.push(p);
                    if (selected.has(p.key)) {
                        const copy = { ...p, key: nextKey++, removed: false };
                        copies.add(copy.key);
                        out.push(copy);
                    }
                });
                pages = out;
                selected = copies;
            });
            toast(`Duplicated ${plural(selected.size, 'page')}`, 'success');
        }
        function reverse() {
            if (pages.length < 2) return;
            mutate(() => pages.reverse());
        }
        function resetEdits() {
            if (!isDirty()) return;
            mutate(() => {
                pages = Array.from({ length: total }, (_, i) => ({ key: nextKey++, src: i, rot: 0, removed: false }));
                selected.clear();
            });
        }
        function undo() {
            if (!undoStack.length) return;
            redoStack.push(snapshot());
            restore(undoStack.pop());
        }
        function redo() {
            if (!redoStack.length) return;
            undoStack.push(snapshot());
            restore(redoStack.pop());
        }

        // Range parsing (1-based positions in the current order, removed pages included)
        function parseRange(text) {
            const result = new Set();
            for (let part of text.split(',')) {
                part = part.trim();
                if (!part) continue;
                const m = part.match(/^(\d+)\s*(?:-\s*(\d+)?)?$/);
                if (!m) throw new Error(`"${part}" isn't a valid page or range.`);
                const start = parseInt(m[1], 10);
                const end = m[2] ? parseInt(m[2], 10) : (part.includes('-') ? pages.length : start);
                if (start < 1 || end < start) throw new Error(`"${part}" isn't a valid range.`);
                if (start > pages.length) throw new Error(`Page ${start} doesn't exist (there are ${pages.length}).`);
                for (let i = start; i <= Math.min(end, pages.length); i++) result.add(pages[i - 1].key);
            }
            if (!result.size) throw new Error('Enter pages like 1-5, 8, 10-');
            return result;
        }
        function rangeSelect() {
            try { selected = parseRange(rangeInput.value); errorEl.textContent = ''; render(); } catch (e) { errorEl.textContent = e.message; }
        }
        function rangeKeep() {
            try {
                const keys = parseRange(rangeInput.value);
                mutate(() => { pages.forEach((p) => { p.removed = !keys.has(p.key); }); selected.clear(); });
            } catch (e) { errorEl.textContent = e.message; }
        }

        // Click / selection
        grid.addEventListener('click', (e) => {
            const el = e.target.closest('.thumb');
            if (!el) return;
            const key = Number(el.dataset.key);
            const page = pages.find((p) => p.key === key);
            const tool = e.target.closest('[data-tool]');
            if (tool) {
                e.stopPropagation();
                if (tool.dataset.tool === 'zoom') lightbox.open(pages.indexOf(page));
                else if (tool.dataset.tool === 'rotate') mutate(() => { page.rot = (page.rot + 90) % 360; });
                else if (tool.dataset.tool === 'remove') mutate(() => { page.removed = !page.removed; });
                return;
            }
            if (e.shiftKey && anchorKey !== null) {
                const a = pages.findIndex((p) => p.key === anchorKey);
                const b = pages.indexOf(page);
                const [lo, hi] = a < b ? [a, b] : [b, a];
                if (!(e.ctrlKey || e.metaKey)) selected.clear();
                for (let i = lo; i <= hi; i++) selected.add(pages[i].key);
            } else {
                if (selected.has(key)) selected.delete(key); else selected.add(key);
                anchorKey = key;
            }
            render();
        });
        grid.addEventListener('dblclick', (e) => {
            const el = e.target.closest('.thumb');
            if (!el || e.target.closest('[data-tool]')) return;
            lightbox.open(pages.findIndex((p) => p.key === Number(el.dataset.key)));
        });
        grid.addEventListener('keydown', (e) => {
            const el = e.target.closest('.thumb');
            if (el && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); el.click(); }
        });

        // Drag reorder (moves the whole selection if the dragged page is selected)
        let dragKeys = null;
        let dropTarget = null;
        let dropAfter = false;
        const clearDropMarks = () => grid.querySelectorAll('.drop-before, .drop-after').forEach((n) => n.classList.remove('drop-before', 'drop-after'));
        grid.addEventListener('dragstart', (e) => {
            const el = e.target.closest('.thumb');
            if (!el) return;
            const key = Number(el.dataset.key);
            dragKeys = selected.has(key) ? pages.filter((p) => selected.has(p.key)).map((p) => p.key) : [key];
            dragKeys.forEach((k) => nodes.get(k)?.classList.add('dragging'));
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', String(key));
        });
        grid.addEventListener('dragover', (e) => {
            if (!dragKeys) return;
            e.preventDefault();
            const el = e.target.closest('.thumb');
            clearDropMarks();
            if (!el) return;
            const rect = el.getBoundingClientRect();
            dropAfter = e.clientX > rect.left + rect.width / 2;
            dropTarget = Number(el.dataset.key);
            el.classList.add(dropAfter ? 'drop-after' : 'drop-before');
        });
        grid.addEventListener('drop', (e) => {
            if (!dragKeys) return;
            e.preventDefault();
            if (dropTarget !== null && !dragKeys.includes(dropTarget)) {
                const moving = dragKeys;
                mutate(() => {
                    const moved = pages.filter((p) => moving.includes(p.key));
                    const rest = pages.filter((p) => !moving.includes(p.key));
                    let at = rest.findIndex((p) => p.key === dropTarget);
                    if (dropAfter) at++;
                    rest.splice(at, 0, ...moved);
                    pages = rest;
                });
            }
        });
        grid.addEventListener('dragend', () => {
            grid.querySelectorAll('.dragging').forEach((n) => n.classList.remove('dragging'));
            clearDropMarks();
            dragKeys = null;
            dropTarget = null;
        });

        // Toolbar
        $('pm-btn-select-all').addEventListener('click', toggleSelectAll);
        $('pm-btn-remove-selected').addEventListener('click', removeSelected);
        $('pm-btn-keep-selected').addEventListener('click', keepSelected);
        $('pm-btn-rotate-selected').addEventListener('click', rotateSelected);
        $('pm-btn-duplicate').addEventListener('click', duplicateSelected);
        $('pm-btn-reverse').addEventListener('click', reverse);
        $('pm-btn-restore-all').addEventListener('click', resetEdits);
        $('pm-btn-range-select').addEventListener('click', rangeSelect);
        $('pm-btn-apply-range').addEventListener('click', rangeKeep);
        rangeInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); rangeSelect(); } });
        undoBtn.addEventListener('click', undo);
        redoBtn.addEventListener('click', redo);
        const savedZoom = storage.get('p2p-thumb-size', 130);
        zoom.value = savedZoom;
        grid.style.setProperty('--thumb', `${savedZoom}px`);
        zoom.addEventListener('input', () => {
            grid.style.setProperty('--thumb', `${zoom.value}px`);
            storage.set('p2p-thumb-size', Number(zoom.value));
        });
        $('shortcuts-btn').addEventListener('click', () => openModal($('shortcuts-modal')));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (editorPanel.hidden || openModals.length) return;
            if (e.target.closest('input, textarea, select')) return;
            const mod = e.ctrlKey || e.metaKey;
            const k = e.key.toLowerCase();
            if (mod && k === 'a') { e.preventDefault(); toggleSelectAll(); }
            else if (mod && k === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
            else if (mod && (k === 'y' || (k === 'z' && e.shiftKey))) { e.preventDefault(); redo(); }
            else if (!mod && (e.key === 'Delete' || e.key === 'Backspace')) { e.preventDefault(); removeSelected(); }
            else if (!mod && k === 'r') { rotateSelected(); }
            else if (!mod && k === 'd') { duplicateSelected(); }
            else if (e.key === 'Escape' && selected.size) { selected.clear(); render(); }
        });

        async function apply() {
            const keep = kept();
            if (!keep.length) {
                errorEl.textContent = 'Keep at least one page.';
                throw new Error('Keep at least one page.');
            }
            const data = await api(`/api/collections/${collectionId}/edit-pages`, {
                method: 'POST',
                json: { keep_pages: keep.map((p) => p.src), rotations_by_position: keep.map((p) => p.rot % 360) },
            });
            collection = data.collection;
            load(collection);
            return collection;
        }

        return {
            load, reset, apply, isDirty,
            get pages() { return pages; },
            thumbUrl,
            setError: (m) => { errorEl.textContent = m; },
        };
    })();

    async function applyEditsIfDirty(button) {
        if (!editor.isDirty()) return true;
        setLoading(button, true);
        try {
            await editor.apply();
            resetExportOptions();
            toast('Page changes applied', 'success');
            return true;
        } catch (e) {
            if (e instanceof SessionExpiredError) { toast(e.message, 'error'); resetAll(); return false; }
            editor.setError(e.message);
            return false;
        } finally {
            setLoading(button, false);
        }
    }

    $('pm-btn-continue').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        if (!(await applyEditsIfDirty(btn))) return;
        showExport();
    });

    // ── Lightbox ────────────────────────────────────────────────
    const lightbox = (() => {
        const el = $('image-modal');
        const img = $('modal-img');
        const loader = $('modal-loader');
        const caption = $('lightbox-caption');
        const prev = $('lightbox-prev');
        const next = $('lightbox-next');
        let index = 0;

        function show() {
            const pages = editor.pages;
            const page = pages[index];
            if (!page) return;
            loader.hidden = false;
            img.style.opacity = '0';
            img.onload = () => { loader.hidden = true; img.style.opacity = '1'; };
            img.src = editor.thumbUrl(page.src, 1.6);
            const rot = page.rot % 360;
            img.style.transform = rot ? `rotate(${rot}deg)${rot % 180 ? ' scale(0.707)' : ''}` : '';
            img.alt = `Page ${index + 1}`;
            caption.textContent = `Page ${index + 1} of ${pages.length}${page.removed ? ' · removed' : ''}${page.src !== index ? ` · originally p.${page.src + 1}` : ''}`;
            prev.disabled = index === 0;
            next.disabled = index >= pages.length - 1;
        }
        function open(i) {
            index = Math.max(0, i);
            show();
            openModal(el);
        }
        prev.addEventListener('click', () => { if (index > 0) { index--; show(); } });
        next.addEventListener('click', () => { if (index < editor.pages.length - 1) { index++; show(); } });
        document.addEventListener('keydown', (e) => {
            if (el.hidden) return;
            if (e.key === 'ArrowLeft') prev.click();
            if (e.key === 'ArrowRight') next.click();
        });
        el.onclose = () => { img.removeAttribute('src'); };
        return { open };
    })();

    // ── Index modal ─────────────────────────────────────────────
    (() => {
        const modal = $('index-modal');
        const help = $('index-mode-help');
        const textarea = $('index-entries-input');
        const errorEl = $('index-error-message');
        const applyBtn = $('index-apply-btn');
        const modes = { off: $('index-off-btn'), automatic: $('index-automatic-btn'), manual: $('index-manual-btn') };
        const HELP = {
            off: 'Remove all bookmarks and the contents page.',
            automatic: 'Use the bookmarks and headings detected in your sources.',
            manual: 'One entry per line: Title | page | level (level 1–3 is optional).',
        };
        let mode = 'automatic';
        function setMode(m) {
            mode = m;
            Object.entries(modes).forEach(([k, b]) => b.setAttribute('aria-checked', String(k === m)));
            help.textContent = HELP[m];
            textarea.hidden = m !== 'manual';
            errorEl.textContent = '';
            if (m === 'manual') textarea.focus();
        }
        Object.entries(modes).forEach(([k, b]) => b.addEventListener('click', () => setMode(k)));

        $('pm-btn-index').addEventListener('click', async (e) => {
            if (!(await applyEditsIfDirty(e.currentTarget))) return;
            setMode('automatic');
            openModal(modal);
        });

        applyBtn.addEventListener('click', async () => {
            const total = editor.pages.length;
            const entries = [];
            if (mode === 'manual') {
                const lines = textarea.value.split('\n').map((l) => l.trim()).filter(Boolean);
                for (const line of lines) {
                    const parts = line.split('|').map((p) => p.trim());
                    const page = Number(parts[1]);
                    const level = parts[2] ? Number(parts[2]) : 1;
                    if (!parts[0] || !Number.isInteger(page) || page < 1 || page > total || ![1, 2, 3].includes(level)) {
                        errorEl.textContent = `Check this line (pages 1–${total}, level 1–3): ${line}`;
                        return;
                    }
                    entries.push({ title: parts[0], page, level });
                }
                if (!entries.length) { errorEl.textContent = 'Add at least one entry.'; return; }
            }
            setLoading(applyBtn, true);
            try {
                const data = await api(`/api/collections/${collectionId}/edit-index`, {
                    method: 'POST',
                    json: { enabled: mode !== 'off', automatic: mode !== 'manual', entries },
                });
                collection = data.collection;
                editor.load(collection);
                resetExportOptions();
                closeModal(modal);
                toast(mode === 'off' ? 'Index removed' : 'Index updated', 'success');
            } catch (err) {
                errorEl.textContent = err.message;
            } finally {
                setLoading(applyBtn, false);
            }
        });
    })();

    // ── Insert modal ────────────────────────────────────────────
    (() => {
        const modal = $('insert-file-modal');
        const fileInputEl = $('insert-file-input');
        const drop = $('insert-file-drop-zone');
        const label = $('insert-file-label');
        const urlEl = $('insert-url-input');
        const position = $('insert-position-select');
        const pageWrap = $('insert-page-number-container');
        const pageEl = $('insert-page-number');
        const errorEl = $('insert-error-message');
        const confirmBtn = $('btn-confirm-insert');
        let chosen = null;

        function setFile(file) {
            chosen = file || null;
            label.textContent = chosen ? chosen.name : 'Choose a PDF or image';
            if (chosen) urlEl.value = '';
            errorEl.textContent = '';
        }

        $('pm-btn-insert-file').addEventListener('click', async (e) => {
            if (!(await applyEditsIfDirty(e.currentTarget))) return;
            setFile(null);
            fileInputEl.value = '';
            urlEl.value = '';
            position.value = 'end';
            pageWrap.hidden = true;
            pageEl.value = '';
            pageEl.max = String(editor.pages.length);
            openModal(modal);
        });
        drop.addEventListener('click', () => fileInputEl.click());
        fileInputEl.addEventListener('change', () => setFile(fileInputEl.files[0]));
        ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('drag-over'); }));
        ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('drag-over'); }));
        drop.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file) setFile(file);
        });
        urlEl.addEventListener('input', () => { if (urlEl.value.trim() && chosen) setFile(null); });
        position.addEventListener('change', () => {
            pageWrap.hidden = position.value !== 'after';
            if (!pageWrap.hidden) pageEl.focus();
        });

        confirmBtn.addEventListener('click', async () => {
            const url = urlEl.value.trim();
            if (!chosen && !url) { errorEl.textContent = 'Choose a file or paste a link.'; return; }
            if (chosen && !SUPPORTED_FILE.test(chosen.name)) { errorEl.textContent = 'Only PDF, PNG, JPG and WEBP files are supported.'; return; }
            let pageIndex = 0;
            const total = editor.pages.length;
            if (position.value === 'after') {
                const n = parseInt(pageEl.value, 10);
                if (!Number.isInteger(n) || n < 1 || n > total) { errorEl.textContent = `Enter a page between 1 and ${total}.`; return; }
                pageIndex = n - 1;
            }
            const form = new FormData();
            if (chosen) form.append('file', chosen);
            else form.append('url', normalizeUrl(url));
            form.append('position', position.value);
            form.append('page_index', String(pageIndex));
            setLoading(confirmBtn, true, url && !chosen ? 'Fetching page…' : 'Inserting…');
            errorEl.textContent = '';
            try {
                const data = await api(`/api/collections/${collectionId}/insert-file`, { method: 'POST', form });
                const before = total;
                collection = data.collection;
                editor.load(collection);
                resetExportOptions();
                closeModal(modal);
                const added = (collection.edited_total_pages || collection.total_pages) - before;
                toast(`Inserted ${plural(Math.max(added, 1), 'page')}`, 'success');
            } catch (err) {
                errorEl.textContent = err.message;
            } finally {
                setLoading(confirmBtn, false, 'Insert');
            }
        });
    })();

    // ── Export ──────────────────────────────────────────────────
    const dl = { sources: $('dl-sources'), pages: $('dl-pages'), size: $('dl-size') };
    const filenameInput = $('custom-filename-input');
    const downloadBtn = $('download-btn');
    const previewFrame = $('pdf-preview-frame');
    const previewLink = $('preview-open-link');
    const opt = {
        numbers: $('opt-page-numbers'),
        position: $('opt-page-number-position'),
        skipFirst: $('opt-skip-first'),
        watermark: $('opt-watermark'),
        password: $('opt-password'),
    };
    const applyExportBtn = $('apply-export-btn');
    const exportStatus = $('export-status');
    const exportBadge = $('export-options-badge');
    let appliedExportKey = '';

    const exportOptions = () => ({
        page_numbers: opt.numbers.checked,
        page_number_position: opt.position.value,
        skip_first_page: opt.skipFirst.checked,
        watermark: opt.watermark.value.trim() || null,
        password: opt.password.value || null,
        author: settings.author.value.trim() || null,
    });
    const exportKey = () => JSON.stringify(exportOptions());
    const hasExportOptions = () => {
        const o = exportOptions();
        return Boolean(o.page_numbers || o.watermark || o.password);
    };
    const exportDirty = () => exportKey() !== appliedExportKey;

    function resetExportOptions() {
        // The server drops the export copy whenever the working PDF changes, so mirror that here.
        appliedExportKey = JSON.stringify({ ...exportOptions(), page_numbers: false, watermark: null, password: null, author: null });
        updateExportStatus();
    }

    function updateExportStatus() {
        exportBadge.hidden = !hasExportOptions();
        if (!hasExportOptions() && !exportDirty()) exportStatus.textContent = '';
        else if (exportDirty()) exportStatus.textContent = 'Options will be applied when you download.';
        else exportStatus.textContent = collection && collection.export_protected ? 'Applied · the download is password-protected.' : 'Applied to the download.';
    }

    Object.values(opt).forEach((el) => el.addEventListener(el.type === 'checkbox' || el.tagName === 'SELECT' ? 'change' : 'input', updateExportStatus));
    opt.numbers.addEventListener('change', () => { $('page-number-options').hidden = !opt.numbers.checked; });

    function downloadUrl({ inline = false } = {}) {
        const params = new URLSearchParams();
        const name = filenameInput.value.trim();
        if (name) params.set('custom_filename', name);
        if (inline) { params.set('inline', '1'); params.set('v', String(thumbVersion)); }
        const q = params.toString();
        return `/api/collections/${collectionId}/download${q ? `?${q}` : ''}`;
    }

    function updateExportView() {
        if (!collection) return;
        const done = collection.items.filter((i) => i.status === 'completed').length;
        dl.sources.textContent = String(done);
        dl.pages.textContent = String(collection.edited_total_pages || collection.total_pages || 0);
        const size = collection.export_size_mb || collection.edited_size_mb || collection.final_pdf_size_mb || 0;
        dl.size.textContent = formatMb(size);
        downloadBtn.href = downloadUrl();
        previewLink.href = downloadUrl({ inline: true });
        updateExportStatus();
    }

    function refreshPreview() {
        const src = downloadUrl({ inline: true });
        // Password-protected exports would prompt inside the frame; preview the working copy instead.
        previewFrame.src = collection && collection.export_protected ? `${src}&working=1` : src;
    }

    function showExport() {
        if (!filenameInput.value.trim()) filenameInput.value = (collection && collection.title) || 'Study Material Collection';
        updateExportView();
        refreshPreview();
        renderIndividual();
        showPanel(exportPanel, 'export');
    }

    async function applyExport() {
        setLoading(applyExportBtn, true);
        try {
            const data = await api(`/api/collections/${collectionId}/finalize`, { method: 'POST', json: exportOptions() });
            collection = data.collection;
            appliedExportKey = exportKey();
            thumbVersion = Date.now();
            updateExportView();
            refreshPreview();
            return true;
        } catch (e) {
            toast(e.message, 'error');
            return false;
        } finally {
            setLoading(applyExportBtn, false);
        }
    }

    applyExportBtn.addEventListener('click', async () => {
        if (await applyExport()) toast(hasExportOptions() ? 'Export options applied' : 'Export options cleared', 'success');
    });

    filenameInput.addEventListener('input', () => { downloadBtn.href = downloadUrl(); });

    downloadBtn.addEventListener('click', async (e) => {
        if (!exportDirty()) return;
        e.preventDefault();
        if (await applyExport()) {
            const a = document.createElement('a');
            a.href = downloadUrl();
            a.download = '';
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    });

    const saveAsBtn = $('save-as-btn');
    if (!window.showSaveFilePicker) {
        saveAsBtn.hidden = true;
    } else {
        saveAsBtn.addEventListener('click', async () => {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: `${filenameInput.value.trim() || 'Page2PDF'}.pdf`,
                    types: [{ description: 'PDF document', accept: { 'application/pdf': ['.pdf'] } }],
                });
                if (exportDirty() && !(await applyExport())) return;
                setLoading(saveAsBtn, true);
                const res = await fetch(downloadUrl());
                if (!res.ok) throw new Error('Could not fetch the PDF.');
                const writable = await handle.createWritable();
                await writable.write(await res.blob());
                await writable.close();
                toast('Saved', 'success');
            } catch (err) {
                if (err && err.name !== 'AbortError') toast(err.message || 'Save failed', 'error');
            } finally {
                setLoading(saveAsBtn, false);
            }
        });
    }

    $('edit-download-btn').addEventListener('click', () => showPanel(editorPanel, 'edit'));
    $('new-btn').addEventListener('click', async () => {
        const ok = await confirmDialog({ title: 'Start a new collection?', body: 'Your current PDF will be cleared from this page. Download it first if you need it.', ok: 'Start new' });
        if (ok) resetAll();
    });

    function renderIndividual() {
        const list = $('individual-downloads-list');
        const done = collection.items.filter((i) => i.status === 'completed' && i.filename);
        $('individual-downloads').hidden = done.length < 2;
        $('individual-count').textContent = `(${done.length})`;
        list.innerHTML = done.map((item) => `
            <li>
                <span class="source-avatar" data-kind="${sourceKind(item)}" style="width:28px;height:28px;${avatarLetter(item).length > 1 ? 'font-size:8px' : ''}">${escapeHtml(avatarLetter(item))}</span>
                <div class="source-body">
                    <div class="source-title">${escapeHtml(item.title || 'Untitled')}</div>
                    <div class="source-meta">${escapeHtml(sourceMeta(item))}</div>
                </div>
                <a href="/api/collections/${encodeURIComponent(collection.id)}/urls/${encodeURIComponent(item.id)}/download" download>${icon('download', 'i-sm')}PDF</a>
            </li>`).join('');
    }

    // ── Global keys ─────────────────────────────────────────────
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && openModals.length) { e.preventDefault(); closeTopModal(); }
    });

    window.addEventListener('beforeunload', (e) => {
        if (collection && (collection.final_pdf_filename || editor.isDirty())) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    renderSources();
})();
