import os
import shutil

TEMPLATE_PATH = "src/templates/tester.html"
ROOT_PATH = "tester.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Navigation Bar tabs
old_nav = """        <div class="nav-tabs">
            <button class="nav-tab-btn active" id="tabNavPlayer" onclick="switchMainPage('player')">
                🎬 Watch & Episodes
            </button>
            <button class="nav-tab-btn" id="tabNavKeys" onclick="switchMainPage('keys')">
                🔑 API Keys & Integration
            </button>
        </div>"""

new_nav = """        <div class="nav-tabs">
            <button class="nav-tab-btn active" id="tabNavPlayer" onclick="switchMainPage('player')">
                🎬 Anime Player
            </button>
            <button class="nav-tab-btn" id="tabNavManga" onclick="switchMainPage('manga')">
                📖 Manga & Manhwa Reader
            </button>
            <button class="nav-tab-btn" id="tabNavHealth" onclick="switchMainPage('health')">
                ⚡ Diagnostics & Health
            </button>
            <button class="nav-tab-btn" id="tabNavKeys" onclick="switchMainPage('keys')">
                🔑 API Keys
            </button>
        </div>"""

if old_nav in content:
    content = content.replace(old_nav, new_nav)
    print("Replaced navigation bar.")
else:
    print("Old nav not matched directly, checking variations...")

# 2. Add Manga & Health CSS before </style>
extra_css = """
        /* ============================================================ */
        /* PAGE 3: MANGA / MANHWA / MANHUA STYLES                      */
        /* ============================================================ */
        .manga-page-view {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .manga-filter-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }

        .manga-type-pills {
            display: flex;
            background: var(--bg-input);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            overflow: hidden;
        }

        .manga-type-btn {
            background: transparent;
            border: none;
            padding: 6px 14px;
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-dim);
            cursor: pointer;
            transition: var(--transition);
        }

        .manga-type-btn.active {
            background: var(--primary);
            color: #ffffff;
        }

        .manga-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
            gap: 16px;
        }

        .manga-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
        }

        .manga-card:hover {
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
        }

        .manga-card-thumb-wrap {
            position: relative;
            width: 100%;
            aspect-ratio: 3/4;
            background: #0f1420;
            overflow: hidden;
        }

        .manga-card-thumb {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }

        .manga-card:hover .manga-card-thumb {
            transform: scale(1.05);
        }

        .badge-type {
            position: absolute;
            top: 8px;
            left: 8px;
            font-size: 0.68rem;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .badge-manhwa { background: #3b82f6; color: #fff; }
        .badge-manga { background: #ec4899; color: #fff; }
        .badge-manhua { background: #f59e0b; color: #000; }

        .manga-card-body {
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .manga-card-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: #fff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .manga-card-meta {
            font-size: 0.74rem;
            color: var(--text-dim);
            display: flex;
            justify-content: space-between;
        }

        /* Manga Reader Container */
        .reader-wrap {
            background: #0b0e14;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .reader-toolbar {
            background: #141923;
            border-bottom: 1px solid var(--border-subtle);
            padding: 10px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            z-index: 10;
        }

        .reader-scroll-view {
            max-height: 80vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            background: #000;
            padding: 10px 0;
            gap: 0;
        }

        .reader-page-img {
            max-width: 800px;
            width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
            background: #111;
            min-height: 200px;
        }

        .reader-single-view {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px 0;
            background: #000;
            min-height: 60vh;
        }

        .reader-single-view img {
            max-width: 800px;
            width: 100%;
            max-height: 85vh;
            object-fit: contain;
        }

        .page-health-indicator {
            font-size: 0.75rem;
            font-weight: 700;
            color: #10b981;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 3px 10px;
            border-radius: 4px;
        }

        /* ============================================================ */
        /* PAGE 4: DIAGNOSTICS & HEALTH CHECK STYLES                    */
        /* ============================================================ */
        .health-page-view {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .health-summary-banner {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }

        .health-metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
        }

        .health-metric-box {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 14px 18px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .health-metric-val {
            font-size: 1.6rem;
            font-weight: 900;
            color: #fff;
        }

        .health-metric-lbl {
            font-size: 0.75rem;
            color: var(--text-dim);
            font-weight: 700;
            text-transform: uppercase;
        }

        .provider-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 14px;
        }

        .provider-status-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 14px 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: var(--transition);
        }

        .provider-status-card.online {
            border-color: rgba(16, 185, 129, 0.4);
            background: linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, var(--bg-surface) 100%);
        }

        .provider-status-card.offline {
            border-color: rgba(239, 68, 68, 0.3);
        }

        .provider-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .provider-name {
            font-size: 0.95rem;
            font-weight: 800;
            color: #fff;
        }

        .status-badge-online {
            font-size: 0.7rem;
            font-weight: 800;
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .status-badge-offline {
            font-size: 0.7rem;
            font-weight: 800;
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .status-badge-degraded {
            font-size: 0.7rem;
            font-weight: 800;
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .provider-body {
            font-size: 0.78rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }

        .sandbox-box {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .json-debug-output {
            background: #090c12;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 14px;
            font-family: monospace;
            font-size: 0.8rem;
            color: #38bdf8;
            max-height: 260px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }
    </style>
"""

content = content.replace("    </style>", extra_css)
print("Injected CSS styles.")

# 3. Add Page Sections for Manga and Health
pages_html = """
        <!-- ============================================================ -->
        <!-- PAGE 3: MANGA / MANHWA / MANHUA TESTER & READER             -->
        <!-- ============================================================ -->
        <section id="page-manga" class="manga-page-view" style="display:none;">

            <!-- Search, Type Filter & Source Selector -->
            <div class="search-section">
                <div class="manga-filter-row">
                    <div class="manga-type-pills">
                        <button class="manga-type-btn active" onclick="setMangaType('all', this)">🌐 All Types</button>
                        <button class="manga-type-btn" onclick="setMangaType('manhwa', this)">🇰🇷 Manhwa</button>
                        <button class="manga-type-btn" onclick="setMangaType('manga', this)">🇯🇵 Manga</button>
                        <button class="manga-type-btn" onclick="setMangaType('manhua', this)">🇨🇳 Manhua</button>
                    </div>

                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:0.78rem; color:var(--text-dim); font-weight:800; text-transform:uppercase;">SOURCE:</span>
                        <div class="provider-select-box">
                            <select id="mangaSourceSelect" onchange="onMangaSourceChange(this.value)">
                                <option value="vortex" selected>Vortex Scans (Webtoons/Manhwa)</option>
                                <option value="toraka">Toraka (ShineiAPI)</option>
                                <option value="mangadex">MangaDex</option>
                                <option value="anilist">AniList Catalog</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="search-bar-wrap" style="margin-top:10px;">
                    <input type="text" class="search-input" id="mangaSearchInput" placeholder="Search Manga, Manhwa, Manhua title..." onkeydown="if(event.key==='Enter') searchManga()">
                    <button class="btn-search" onclick="searchManga()">Search</button>
                </div>

                <div class="presets-row">
                    <span style="font-size:0.75rem; color:var(--text-dim); font-weight:700;">PRESETS:</span>
                    <button class="preset-pill" onclick="quickMangaPreset('the-genius-wants-to-be-ordinary!', 'The Genius Wants to be Ordinary!', 'vortex')">⚡ The Genius Wants to be Ordinary</button>
                    <button class="preset-pill" onclick="quickMangaPreset('the-greatest-estate-developer', 'The Greatest Estate Developer', 'toraka')">🏰 The Greatest Estate Developer</button>
                    <button class="preset-pill" onclick="quickMangaPreset('solo-leveling', 'Solo Leveling', 'vortex')">🗡️ Solo Leveling</button>
                    <button class="preset-pill" onclick="quickMangaPreset('omniscient-reader', 'Omniscient Reader', 'vortex')">📖 Omniscient Reader</button>
                    <button class="preset-pill" onclick="quickMangaPreset('tower-of-god', 'Tower of God', 'vortex')">🗼 Tower of God</button>
                </div>
            </div>

            <!-- Series Details & Chapter Selector Box -->
            <div class="search-section" id="mangaDetailCard" style="display:none;">
                <div style="display:flex; gap:18px; flex-wrap:wrap; align-items:center;">
                    <img id="mangaCoverImg" src="" style="width:72px; height:96px; object-fit:cover; border-radius:6px; border:1px solid var(--border-subtle);">
                    <div style="flex:1; display:flex; flex-direction:column; gap:6px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="badge-type badge-manhwa" id="mangaTypeBadge">MANHWA</span>
                            <span style="font-size:1.15rem; font-weight:800; color:#fff;" id="mangaTitleDisplay">Title</span>
                        </div>
                        <span style="font-size:0.78rem; color:var(--text-dim);" id="mangaMetaDisplay">Chapters available</span>
                    </div>

                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:0.8rem; font-weight:800; color:#94a3b8;">CHAPTER:</span>
                        <select id="mangaChapterSelect" class="provider-select-box" style="padding:8px 14px; background:#121826; color:#fff; border:1px solid #28334a; border-radius:8px;" onchange="loadChapterPages(this.value)">
                            <option value="">Select Chapter</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- Interactive Chapter Page Reader / Tester -->
            <div class="reader-wrap" id="mangaReaderWrap" style="display:none;">
                <div class="reader-toolbar">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-weight:800; color:#fff; font-size:0.92rem;" id="readerChapterTitle">Chapter Reader</span>
                        <span class="page-health-indicator" id="readerPageHealth">Loading pages...</span>
                    </div>

                    <div style="display:flex; align-items:center; gap:10px;">
                        <div class="manga-type-pills">
                            <button class="manga-type-btn active" id="btnModeWebtoon" onclick="setReaderMode('webtoon')">📜 Webtoon Scroll</button>
                            <button class="manga-type-btn" id="btnModeSingle" onclick="setReaderMode('single')">📖 Single Page</button>
                        </div>

                        <!-- Single page controls -->
                        <div id="singlePageNavControls" style="display:none; align-items:center; gap:6px;">
                            <button class="btn-sm-action" onclick="prevSinglePage()">◀ Prev</button>
                            <span style="font-size:0.8rem; color:#fff;" id="singlePageNumDisplay">1 / 1</span>
                            <button class="btn-sm-action" onclick="nextSinglePage()">Next ▶</button>
                        </div>
                    </div>
                </div>

                <!-- Webtoon Continuous Scroll Container -->
                <div class="reader-scroll-view" id="readerScrollView"></div>

                <!-- Single Page View Container -->
                <div class="reader-single-view" id="readerSingleView" style="display:none;">
                    <img id="readerSingleImg" src="" alt="Page">
                </div>
            </div>

            <!-- Manga Search & Browse Grid -->
            <div class="manga-grid" id="mangaBrowseGrid"></div>

        </section>


        <!-- ============================================================ -->
        <!-- PAGE 4: DIAGNOSTICS & SYSTEM HEALTH TESTER                   -->
        <!-- ============================================================ -->
        <section id="page-health" class="health-page-view" style="display:none;">

            <div class="health-summary-banner">
                <div style="display:flex; flex-direction:column; gap:4px;">
                    <span style="font-size:1.2rem; font-weight:900; color:#fff;">Live Provider & Extractor Diagnostics</span>
                    <span style="font-size:0.82rem; color:var(--text-muted);">Real-time status, latency, and response checker across all anime & manga sources.</span>
                </div>
                <button class="btn-search" style="padding:10px 20px;" onclick="runDiagnostics()">⚡ Run Full Diagnostics Now</button>
            </div>

            <!-- Quick Stats -->
            <div class="health-metrics-row">
                <div class="health-metric-box">
                    <span class="health-metric-val" id="diagAnimeStat">-- / 11</span>
                    <span class="health-metric-lbl">Anime Extractors</span>
                </div>
                <div class="health-metric-box">
                    <span class="health-metric-val" id="diagMangaStat" style="color:#10b981;">4 / 4</span>
                    <span class="health-metric-lbl">Manga / Catalog Sources</span>
                </div>
                <div class="health-metric-box">
                    <span class="health-metric-val" id="diagLatencyStat">-- ms</span>
                    <span class="health-metric-lbl">Average Latency</span>
                </div>
                <div class="health-metric-box">
                    <span class="health-metric-val" id="diagTimeStat" style="font-size:1.1rem; color:#60a5fa;">Ready</span>
                    <span class="health-metric-lbl">Last Inspection</span>
                </div>
            </div>

            <!-- Provider Status Grid -->
            <div style="display:flex; flex-direction:column; gap:10px;">
                <span style="font-size:0.9rem; font-weight:800; color:#fff;">ALL REGISTERED PROVIDERS</span>
                <div class="provider-cards-grid" id="diagnosticsProvidersGrid">
                    <div style="grid-column: 1 / -1; text-align:center; padding:30px; color:var(--text-dim);">
                        Click "Run Full Diagnostics Now" above to ping all upstream extractors and APIs.
                    </div>
                </div>
            </div>

            <!-- Custom Request Playground -->
            <div class="sandbox-box">
                <span style="font-size:0.95rem; font-weight:800; color:#fff;">Live Endpoint Sandbox Tester</span>
                <div class="search-bar-wrap">
                    <input type="text" class="search-input" id="sandboxUrlInput" value="/manga/popular?type=manhwa" placeholder="/anime/extract/21827?e=1 or /manga/search?q=solo">
                    <button class="btn-search" onclick="runSandboxRequest()">Send Request</button>
                </div>
                <div class="json-debug-output" id="sandboxJsonOutput">// Response JSON will appear here after clicking Send Request</div>
            </div>

        </section>
"""

# Insert pages before </main>
content = content.replace("    </main>", pages_html + "\n    </main>")
print("Injected Manga and Health page markup.")

# 4. Add JavaScript for Manga and Diagnostics before </script>
extra_js = """
        // ============================================================
        // MANGA / MANHWA / MANHUA CLIENT LOGIC
        // ============================================================
        let currentMangaType = 'all';
        let currentMangaSource = 'vortex';
        let activeChapterPages = [];
        let currentSinglePageIndex = 0;
        let readerMode = 'webtoon';

        function setMangaType(type, btn) {
            currentMangaType = type;
            document.querySelectorAll('.manga-type-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            searchManga();
        }

        function onMangaSourceChange(source) {
            currentMangaSource = source;
            searchManga();
        }

        async function searchManga() {
            const query = document.getElementById('mangaSearchInput').value.trim();
            const grid = document.getElementById('mangaBrowseGrid');
            grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:#94a3b8;">Searching titles...</div>';

            try {
                let url = `${API_BASE}/manga/search?q=${encodeURIComponent(query)}&type=${currentMangaType}&source=${currentMangaSource}`;
                if (!query) {
                    url = `${API_BASE}/manga/popular?type=${currentMangaType}&source=${currentMangaSource}`;
                }
                const res = await fetch(url);
                const data = await res.json();
                const results = data.results || [];
                renderMangaGrid(results);
            } catch (err) {
                grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#ef4444;">Failed to load series: ${err.message}</div>`;
            }
        }

        function renderMangaGrid(items) {
            const grid = document.getElementById('mangaBrowseGrid');
            if (!items || items.length === 0) {
                grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:#94a3b8;">No manga/manhwa series found.</div>';
                return;
            }

            grid.innerHTML = items.map(item => {
                const typeClass = (item.type || '').toLowerCase().includes('manhwa') ? 'badge-manhwa' :
                                  (item.type || '').toLowerCase().includes('manhua') ? 'badge-manhua' : 'badge-manga';
                const typeLabel = item.type || 'MANGA';
                const cover = item.cover || 'https://via.placeholder.com/300x400?text=No+Cover';
                const safeTitle = escapeHtml(item.title);
                const safeSlug = escapeHtml(item.slug || item.id);
                const source = escapeHtml(item.source || currentMangaSource);

                return `
                    <div class="manga-card" onclick="selectMangaSeries('${safeSlug}', '${safeTitle}', '${source}', '${escapeHtml(cover)}')">
                        <div class="manga-card-thumb-wrap">
                            <span class="badge-type ${typeClass}">${typeLabel}</span>
                            <img class="manga-card-thumb" src="${cover}" alt="${safeTitle}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x400?text=Image+Unavailable'">
                        </div>
                        <div class="manga-card-body">
                            <span class="manga-card-title" title="${safeTitle}">${safeTitle}</span>
                            <div class="manga-card-meta">
                                <span>${item.chapters_count ? item.chapters_count + ' ch' : (item.status || 'Ongoing')}</span>
                                <span style="text-transform:capitalize;">${source}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function quickMangaPreset(slug, title, source) {
            document.getElementById('mangaSourceSelect').value = source;
            currentMangaSource = source;
            selectMangaSeries(slug, title, source);
        }

        async function selectMangaSeries(slug, title, source, coverUrl = '') {
            const card = document.getElementById('mangaDetailCard');
            card.style.display = 'block';
            document.getElementById('mangaTitleDisplay').textContent = title;
            document.getElementById('mangaMetaDisplay').textContent = `Fetching chapters from ${source}...`;
            if (coverUrl) {
                document.getElementById('mangaCoverImg').src = coverUrl;
            }

            try {
                const res = await fetch(`${API_BASE}/manga/info/${encodeURIComponent(slug)}?source=${source}`);
                const data = await res.json();
                const chapters = data.chapters || [];

                document.getElementById('mangaMetaDisplay').textContent = `${chapters.length} chapters available on ${source}`;
                if (data.cover && !coverUrl) {
                    document.getElementById('mangaCoverImg').src = data.cover;
                }

                const select = document.getElementById('mangaChapterSelect');
                if (chapters.length === 0) {
                    select.innerHTML = '<option value="">No unlocked chapters</option>';
                    return;
                }

                select.innerHTML = chapters.map(c => `
                    <option value="${c.id}" ${c.is_locked ? 'disabled' : ''}>
                        Chapter ${c.number || ''} ${c.is_locked ? '🔒 (Locked)' : ''}
                    </option>
                `).join('');

                // Automatically load the first available chapter
                const firstFree = chapters.find(c => !c.is_locked) || chapters[0];
                if (firstFree) {
                    select.value = firstFree.id;
                    loadChapterPages(firstFree.id);
                }
            } catch (err) {
                document.getElementById('mangaMetaDisplay').textContent = `Error loading chapters: ${err.message}`;
            }
        }

        async function loadChapterPages(chapterId) {
            if (!chapterId) return;
            const readerWrap = document.getElementById('mangaReaderWrap');
            const scrollView = document.getElementById('readerScrollView');
            const healthBadge = document.getElementById('readerPageHealth');

            readerWrap.style.display = 'flex';
            scrollView.innerHTML = '<div style="color:#94a3b8; padding:50px;">Loading pages via image proxy...</div>';
            healthBadge.textContent = 'Fetching pages...';

            try {
                const res = await fetch(`${API_BASE}/manga/chapter/${chapterId}?source=${currentMangaSource}`);
                const data = await res.json();
                activeChapterPages = data.pages || [];
                document.getElementById('readerChapterTitle').textContent = `Chapter ${data.number || ''} (${activeChapterPages.length} Pages)`;

                if (activeChapterPages.length === 0) {
                    scrollView.innerHTML = '<div style="color:#ef4444; padding:50px;">No images found in this chapter.</div>';
                    healthBadge.textContent = '0 Pages';
                    return;
                }

                let loadedCount = 0;
                let failedCount = 0;
                const total = activeChapterPages.length;

                function updateHealth() {
                    const percent = Math.round((loadedCount / total) * 100);
                    healthBadge.textContent = `${loadedCount} / ${total} Pages Loaded (${percent}% Health)`;
                    if (failedCount > 0) {
                        healthBadge.style.color = '#ef4444';
                    } else if (loadedCount === total) {
                        healthBadge.style.color = '#10b981';
                    }
                }

                scrollView.innerHTML = '';
                activeChapterPages.forEach((rawUrl, idx) => {
                    const proxiedUrl = `${API_BASE}/proxy_image?url=${encodeURIComponent(rawUrl)}&referer=${encodeURIComponent(data.referer || 'https://vortexscans.org/')}`;
                    const img = document.createElement('img');
                    img.className = 'reader-page-img';
                    img.loading = idx < 3 ? 'eager' : 'lazy';
                    img.src = proxiedUrl;
                    img.alt = `Page ${idx + 1}`;
                    img.onload = () => { loadedCount++; updateHealth(); };
                    img.onerror = () => { failedCount++; updateHealth(); };
                    scrollView.appendChild(img);
                });

                currentSinglePageIndex = 0;
                updateSinglePageView();

            } catch (err) {
                scrollView.innerHTML = `<div style="color:#ef4444; padding:50px;">Error loading chapter pages: ${err.message}</div>`;
            }
        }

        function setReaderMode(mode) {
            readerMode = mode;
            const scrollView = document.getElementById('readerScrollView');
            const singleView = document.getElementById('readerSingleView');
            const singleNav = document.getElementById('singlePageNavControls');
            const btnWebtoon = document.getElementById('btnModeWebtoon');
            const btnSingle = document.getElementById('btnModeSingle');

            if (mode === 'webtoon') {
                scrollView.style.display = 'flex';
                singleView.style.display = 'none';
                singleNav.style.display = 'none';
                btnWebtoon.classList.add('active');
                btnSingle.classList.remove('active');
            } else {
                scrollView.style.display = 'none';
                singleView.style.display = 'flex';
                singleNav.style.display = 'flex';
                btnWebtoon.classList.remove('active');
                btnSingle.classList.add('active');
                updateSinglePageView();
            }
        }

        function updateSinglePageView() {
            if (activeChapterPages.length === 0) return;
            const singleImg = document.getElementById('readerSingleImg');
            const pageNumDisplay = document.getElementById('singlePageNumDisplay');
            const rawUrl = activeChapterPages[currentSinglePageIndex];
            singleImg.src = `${API_BASE}/proxy_image?url=${encodeURIComponent(rawUrl)}`;
            pageNumDisplay.textContent = `${currentSinglePageIndex + 1} / ${activeChapterPages.length}`;
        }

        function prevSinglePage() {
            if (currentSinglePageIndex > 0) {
                currentSinglePageIndex--;
                updateSinglePageView();
            }
        }

        function nextSinglePage() {
            if (currentSinglePageIndex < activeChapterPages.length - 1) {
                currentSinglePageIndex++;
                updateSinglePageView();
            }
        }

        // Keyboard arrow navigation for single page reading
        window.addEventListener('keydown', (e) => {
            if (readerMode === 'single' && document.getElementById('page-manga').style.display !== 'none') {
                if (e.key === 'ArrowRight' || e.key === ' ') {
                    nextSinglePage();
                } else if (e.key === 'ArrowLeft') {
                    prevSinglePage();
                }
            }
        });


        // ============================================================
        // DIAGNOSTICS & SYSTEM HEALTH LOGIC
        // ============================================================
        async function runDiagnostics() {
            const grid = document.getElementById('diagnosticsProvidersGrid');
            grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:#38bdf8;">⚡ Pinging all upstream APIs and extractors concurrently...</div>';

            try {
                const res = await fetch(`${API_BASE}/health/all`);
                const data = await res.json();

                document.getElementById('diagAnimeStat').textContent = `${data.anime_online} / ${data.anime_total}`;
                document.getElementById('diagMangaStat').textContent = `${data.manga_online} / ${data.manga_total}`;
                document.getElementById('diagTimeStat').textContent = data.timestamp;

                const providers = data.providers || [];
                const latencies = providers.filter(p => p.latency_ms).map(p => p.latency_ms);
                const avgLat = latencies.length ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : 0;
                document.getElementById('diagLatencyStat').textContent = `${avgLat} ms`;

                grid.innerHTML = providers.map(p => {
                    const isOnline = p.status === 'online';
                    const isDegraded = p.status === 'degraded' || p.status === 'empty';
                    const cardClass = isOnline ? 'online' : (isDegraded ? 'degraded' : 'offline');
                    const badgeClass = isOnline ? 'status-badge-online' : (isDegraded ? 'status-badge-degraded' : 'status-badge-offline');
                    const badgeLabel = isOnline ? 'ONLINE 🟢' : (isDegraded ? 'EMPTY / DEGRADED 🟡' : 'OFFLINE 🔴');

                    return `
                        <div class="provider-status-card ${cardClass}">
                            <div class="provider-head">
                                <span class="provider-name">${escapeHtml(p.name)}</span>
                                <span class="${badgeClass}">${badgeLabel}</span>
                            </div>
                            <div class="provider-body">
                                <span>Category: ${escapeHtml(p.category || 'extractor')}</span>
                                <span>⚡ ${p.latency_ms || 0} ms</span>
                            </div>
                            <div style="font-size:0.75rem; color:#94a3b8; border-top:1px solid rgba(255,255,255,0.06); padding-top:6px;">
                                ${escapeHtml(p.message || '')}
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#ef4444;">Diagnostics failed: ${err.message}</div>`;
            }
        }

        async function runSandboxRequest() {
            const urlInput = document.getElementById('sandboxUrlInput').value.trim();
            const output = document.getElementById('jsonDebugOutput') || document.getElementById('sandboxJsonOutput');
            output.textContent = "Loading request...";

            try {
                const targetUrl = urlInput.startsWith('http') ? urlInput : `${API_BASE}${urlInput.startsWith('/') ? '' : '/'}${urlInput}`;
                const t0 = performance.now();
                const res = await fetch(targetUrl);
                const dur = Math.round(performance.now() - t0);
                const json = await res.json();
                output.textContent = `// HTTP ${res.status} OK in ${dur}ms\\n` + JSON.stringify(json, null, 2);
            } catch (err) {
                output.textContent = `// Error executing request:\\n${err.message}`;
            }
        }
"""

content = content.replace("    </script>", extra_js + "\n    </script>")
print("Injected Manga and Diagnostics JavaScript.")

# 5. Update switchMainPage function to handle player, manga, health, keys
old_switch = """        function switchMainPage(page) {
            document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('page-player').style.display = 'none';
            document.getElementById('page-keys').style.display = 'none';

            if (page === 'player') {
                document.getElementById('tabNavPlayer').classList.add('active');
                document.getElementById('page-player').style.display = 'flex';
            } else if (page === 'keys') {
                document.getElementById('tabNavKeys').classList.add('active');
                document.getElementById('page-keys').style.display = 'flex';
                fetchApiKeys();
            }
        }"""

new_switch = """        function switchMainPage(page) {
            document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('page-player').style.display = 'none';
            const pageManga = document.getElementById('page-manga');
            if (pageManga) pageManga.style.display = 'none';
            const pageHealth = document.getElementById('page-health');
            if (pageHealth) pageHealth.style.display = 'none';
            document.getElementById('page-keys').style.display = 'none';

            if (page === 'player') {
                document.getElementById('tabNavPlayer').classList.add('active');
                document.getElementById('page-player').style.display = 'flex';
            } else if (page === 'manga') {
                document.getElementById('tabNavManga').classList.add('active');
                if (pageManga) {
                    pageManga.style.display = 'flex';
                    if (!document.getElementById('mangaBrowseGrid').hasChildNodes()) {
                        searchManga();
                    }
                }
            } else if (page === 'health') {
                document.getElementById('tabNavHealth').classList.add('active');
                if (pageHealth) {
                    pageHealth.style.display = 'flex';
                }
            } else if (page === 'keys') {
                document.getElementById('tabNavKeys').classList.add('active');
                document.getElementById('page-keys').style.display = 'flex';
                fetchApiKeys();
            }
        }"""

if old_switch in content:
    content = content.replace(old_switch, new_switch)
    print("Updated switchMainPage function.")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

shutil.copyfile(TEMPLATE_PATH, ROOT_PATH)
print("Successfully wrote updated tester.html in src/templates and root!")
