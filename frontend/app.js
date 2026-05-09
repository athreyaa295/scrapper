// Update the production URL below after deploying the backend to Render
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '')
    ? 'http://localhost:8000/api'
    : 'https://heta-backend.onrender.com/api';

document.addEventListener('DOMContentLoaded', () => {
    let allEvents = [];
    let currentCategory = 'All';
    let currentSearch = '';

    const eventsGrid = document.getElementById('events-grid');
    const searchInput = document.getElementById('search-input');
    const navItems = document.querySelectorAll('.nav-item');
    const scanBtn = document.getElementById('scan-btn');
    const statusIndicator = document.getElementById('status-indicator');
    const totalCountEl = document.getElementById('total-count');
    const urgentCountEl = document.getElementById('urgent-count');
    const logTerminal = document.getElementById('log-terminal');
    const logContent = document.getElementById('log-content');
    const closeLogsBtn = document.getElementById('close-logs');
    const template = document.getElementById('event-card-template');

    // Initialize
    fetchEvents();

    // Event Listeners
    searchInput.addEventListener('input', (e) => {
        currentSearch = e.target.value.toLowerCase();
        renderEvents();
    });

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            currentCategory = item.getAttribute('data-category');
            renderEvents();
        });
    });

    scanBtn.addEventListener('click', async () => {
        if (scanBtn.disabled) return;
        
        try {
            scanBtn.disabled = true;
            statusIndicator.classList.add('active');
            logTerminal.classList.add('active');
            logContent.innerHTML = 'Starting Heta Deep Scan...';
            scanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';
            
            await fetch(`${API_BASE}/scrape`, { method: 'POST' });
            
            // Poll for results and logs
            const pollInterval = setInterval(async () => {
                const healthRes = await fetch(`${API_BASE}/health`);
                const health = await healthRes.json();
                
                const logsRes = await fetch(`${API_BASE}/logs`);
                const logsData = await logsRes.json();
                if (logsData.logs) {
                    logContent.innerHTML = logsData.logs.join('\n');
                    logContent.scrollTop = logContent.scrollHeight;
                }
                
                if (!health.scraping) {
                    clearInterval(pollInterval);
                    await fetchEvents();
                    statusIndicator.classList.remove('active');
                    scanBtn.disabled = false;
                    scanBtn.innerHTML = '<i class="fa-solid fa-radar"></i> Deep Scan';
                }
            }, 2000);
            
        } catch (error) {
            console.error('Scan error:', error);
            statusIndicator.classList.remove('active');
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<i class="fa-solid fa-radar"></i> Deep Scan';
        }
    });

    closeLogsBtn.addEventListener('click', () => {
        logTerminal.classList.remove('active');
    });

    async function fetchEvents() {
        try {
            statusIndicator.classList.add('active');
            const response = await fetch(`${API_BASE}/events`);
            const data = await response.json();
            allEvents = data;
            
            updateStats();
            renderEvents();
            statusIndicator.classList.remove('active');
        } catch (error) {
            console.error('Error fetching events:', error);
            statusIndicator.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Backend server not reachable. Ensure API is running at localhost:8000.';
            // Load some dummy data for preview if backend is dead
            allEvents = [
                {
                    title: "Google Summer of Code 2026",
                    category: "Internship",
                    priority: "🔴 HIGH PRIORITY",
                    source: "Google",
                    raw_date_text: "Apply ASAP",
                    description: "Global, online program focused on bringing new contributors into open source software development.",
                    registration_link: "#"
                },
                {
                    title: "NeurIPS 2026 Call for Papers",
                    category: "AI Research",
                    priority: "🟡 MEDIUM PRIORITY",
                    source: "NeurIPS",
                    raw_date_text: "Deadline in 14 days",
                    description: "The premier AI/ML conference. Submit your latest research papers.",
                    registration_link: "#"
                }
            ];
            updateStats();
            renderEvents();
        }
    }

    function updateStats() {
        totalCountEl.textContent = allEvents.length;
        const urgentCount = allEvents.filter(e => e.priority && e.priority.includes('HIGH')).length;
        urgentCountEl.textContent = urgentCount;
    }

    function renderEvents() {
        eventsGrid.innerHTML = '';
        
        let filtered = allEvents.filter(event => {
            const matchesCat = currentCategory === 'All' || event.category === currentCategory || 
                             (currentCategory === 'AI Research' && event.category === 'AI Research');
            const matchesSearch = (event.title || '').toLowerCase().includes(currentSearch) || 
                                (event.source || '').toLowerCase().includes(currentSearch);
            return matchesCat && matchesSearch;
        });

        if (filtered.length === 0) {
            eventsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.5); padding: 40px;">No opportunities found matching your criteria.</div>';
            return;
        }

        filtered.forEach(event => {
            const clone = template.content.cloneNode(true);
            
            // Populate data
            const catClass = (event.category || 'Default').replace(/\s+/g, '-');
            const catEl = clone.querySelector('.category-badge');
            catEl.textContent = event.category || 'Event';
            catEl.classList.add(`cat-${catClass}`);
            
            // If category class doesn't exist, fallback
            if (!catEl.className.includes(`cat-${catClass}`)) {
                catEl.classList.add('cat-Default');
            }

            const pri = event.priority || '🟢 LOW PRIORITY';
            const priType = pri.includes('HIGH') ? 'HIGH' : (pri.includes('MEDIUM') ? 'MEDIUM' : 'LOW');
            const priEl = clone.querySelector('.priority-badge');
            priEl.textContent = pri.replace(/[^A-Za-z\s]/g, '').trim();
            priEl.classList.add(`pri-${priType}`);

            clone.querySelector('.event-title').textContent = event.title || 'Unknown Title';
            clone.querySelector('.source-text').textContent = event.source || 'Web';
            
            const descEl = clone.querySelector('.event-description');
            if (event.description) {
                descEl.textContent = event.description;
            } else {
                descEl.style.display = 'none';
            }

            clone.querySelector('.deadline-text').textContent = event.raw_date_text || 'N/A';
            
            const btn = clone.querySelector('.apply-btn');
            btn.href = event.registration_link || '#';
            btn.classList.add(`btn-${catClass}`);

            const autoBtn = clone.querySelector('.auto-apply-btn');
            autoBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                if (autoBtn.classList.contains('loading') || autoBtn.classList.contains('success')) return;

                autoBtn.classList.add('loading');
                autoBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Applying...';

                try {
                    const res = await fetch(`${API_BASE}/auto-apply`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: event.registration_link })
                    });
                    const result = await res.json();
                    
                    if (result.status === 'success') {
                        autoBtn.classList.remove('loading');
                        autoBtn.classList.add('success');
                        autoBtn.innerHTML = '<i class="fa-solid fa-check"></i> Applied';
                    } else {
                        autoBtn.classList.remove('loading');
                        autoBtn.innerHTML = '<i class="fa-solid fa-user"></i> Manual';
                        autoBtn.title = result.message || 'Manual authentication required';
                    }
                } catch (err) {
                    console.error('Auto-apply failed:', err);
                    autoBtn.classList.remove('loading');
                    autoBtn.innerHTML = '<i class="fa-solid fa-robot"></i> Auto-Apply';
                }
            });

            eventsGrid.appendChild(clone);
        });
    }
});
