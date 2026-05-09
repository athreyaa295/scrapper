"""
Heta AI — Full-Spectrum Scraper
=====================================
Scrapes: Hackathons, Conferences, AI Research Papers, AI News,
         AI Technology, Startups, Internships
"""

import uuid, asyncio, re, json, traceback
from datetime import datetime
from typing import List, Dict, Any
import requests
from models import Event
from ai_engine import extract_deadline_and_validate

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ═══════════════════════════════════════════════════════════════
#  HACKATHONS
# ═══════════════════════════════════════════════════════════════
def scrape_devfolio() -> List[Dict[str, Any]]:
    events = []
    try:
        print("  -> Devfolio API...")
        res = requests.post(
            "https://api.devfolio.co/api/search/hackathons",
            json={"type": "application_open", "from": 0, "size": 100},
            headers=HEADERS, timeout=20,
        )
        if res.status_code == 200:
            hits = res.json().get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                name = src.get("name", "Unknown Hackathon")
                slug = src.get("slug", "")
                link = f"https://{slug}.devfolio.co" if slug else "https://devfolio.co/hackathons"
                reg_ends = src.get("hackathon_setting", {}).get("reg_ends_at")
                raw = f"Registration ends {reg_ends}" if reg_ends else "Apply ASAP, rolling admissions"
                events.append({"title": name, "link": link, "raw_date_text": raw,
                    "source": "Devfolio", "category": "Hackathon", "description": src.get("desc", "")})
    except Exception as e:
        print(f"  [WARN] Devfolio: {e}")
    return events

def _scrape_devpost_fallback() -> List[Dict[str, Any]]:
    events = []
    try:
        res = requests.get("https://devpost.com/hackathons?status[]=open&status[]=upcoming", headers=HEADERS, timeout=20)
        if res.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(res.text, "html.parser")
            for tile in soup.select(".hackathon-tile, article"):
                title_el = tile.select_one("h3, h2, .title")
                link_el = tile if tile.name == "a" else tile.select_one("a")
                title = title_el.get_text(strip=True) if title_el else ""
                href = link_el.get("href", "") if link_el else ""
                if href and not href.startswith("http"): href = f"https://devpost.com{href}"
                if title:
                    events.append({"title": title, "link": href or "https://devpost.com/hackathons",
                        "raw_date_text": "Open for submissions", "source": "Devpost", "category": "Hackathon"})
    except Exception as e:
        print(f"  [WARN] Devpost fallback: {e}")
    return events

async def scrape_devpost() -> List[Dict[str, Any]]:
    if not PLAYWRIGHT_AVAILABLE: return _scrape_devpost_fallback()
    events = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://devpost.com/hackathons?status[]=open&status[]=upcoming", wait_until="networkidle", timeout=30000)
            tiles = await page.query_selector_all(".hackathon-tile, article")
            for tile in tiles:
                title_el = await tile.query_selector("h3, .title")
                link_el = await tile.query_selector("a")
                status_el = await tile.query_selector(".submission-period, .dates")
                title = (await title_el.inner_text()).strip() if title_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                status = (await status_el.inner_text()).strip() if status_el else "Open"
                if href and not href.startswith("http"): href = f"https://devpost.com{href}"
                if title and len(title) > 3:
                    events.append({"title": title, "link": href or "https://devpost.com/hackathons",
                        "raw_date_text": status, "source": "Devpost", "category": "Hackathon"})
            await browser.close()
    except Exception as e:
        print(f"  [WARN] Devpost Playwright: {e}")
        events = _scrape_devpost_fallback()
    return events

async def scrape_mlh() -> List[Dict[str, Any]]:
    events = []
    if not PLAYWRIGHT_AVAILABLE: return events
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://mlh.io/seasons/2026/events", wait_until="networkidle", timeout=30000)
            cards = await page.query_selector_all(".event-wrapper, .event")
            for card in cards:
                title_el = await card.query_selector("h3, .event-name")
                title = (await title_el.inner_text()).strip() if title_el else ""
                if title and len(title) > 3 and not _is_bad_title(title):
                    events.append({"title": title, "link": "https://mlh.io/events",
                        "raw_date_text": "Register by next month", "source": "MLH", "category": "Hackathon"})
            await browser.close()
    except Exception as e:
        print(f"  [WARN] MLH Playwright: {e}")
    return events

async def scrape_unstop() -> List[Dict[str, Any]]:
    events = []
    try:
        res = requests.get("https://unstop.com/api/public/opportunity/search-new?opportunity=hackathons&per_page=100",
            headers=HEADERS, timeout=15)
        if res.status_code == 200:
            for opp in res.json().get("data", {}).get("data", []):
                title = opp.get("title", "")
                slug = opp.get("public_url", "") or opp.get("seo_url", "")
                link = f"https://unstop.com/{slug}" if slug else "https://unstop.com/hackathons"
                deadline = opp.get("regnRequirements", {}).get("end_regn_dt", "")
                events.append({"title": title, "link": link,
                    "raw_date_text": f"Registration ends {deadline}" if deadline else "Apply ASAP",
                    "source": "Unstop", "category": "Hackathon"})
    except Exception as e:
        print(f"  [WARN] Unstop: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  INTERNSHIPS
# ═══════════════════════════════════════════════════════════════
def scrape_github_internships() -> List[Dict[str, Any]]:
    events = []
    try:
        res = requests.get("https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md", timeout=20)
        if res.status_code == 200:
            for line in res.text.split("\n"):
                if line.startswith("|") and "Company" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 6:
                        if "🔒" in parts[4]: continue
                        company = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', parts[1]).replace('*', '').strip()
                        role = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', parts[2]).strip()
                        link_match = re.search(r'href="([^"]+)"', parts[4]) or re.search(r'\]\(([^)]+)\)', parts[4])
                        link = link_match.group(1) if link_match else "https://github.com/SimplifyJobs/Summer2025-Internships"
                        if company and role:
                            events.append({"title": f"{company} — {role}", "link": link,
                                "raw_date_text": "Apply ASAP, rolling admissions", "source": "GitHub (Simplify)", "category": "Internship"})
    except Exception as e:
        print(f"  [WARN] GitHub: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  AI NEWS (RSS Feeds)
# ═══════════════════════════════════════════════════════════════
def scrape_ai_news() -> List[Dict[str, Any]]:
    events = []
    if not feedparser: return events
    feeds = [
        ("https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en", "Google News AI"),
        ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI"),
        ("https://venturebeat.com/category/ai/feed/", "VentureBeat AI"),
        ("https://www.artificialintelligence-news.com/feed/", "AI News"),
        ("https://feeds.feedburner.com/TheHackersNews", "The Hacker News"),
    ]
    for url, source in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                published = entry.get("published", "")
                if title and len(title) > 5:
                    events.append({"title": title, "link": link,
                        "raw_date_text": published if published else "Today",
                        "source": source, "category": "AI News",
                        "description": entry.get("summary", "")[:200]})
        except Exception as e:
            print(f"  [WARN] {source}: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  AI RESEARCH PAPERS (arXiv RSS)
# ═══════════════════════════════════════════════════════════════
def scrape_ai_research() -> List[Dict[str, Any]]:
    events = []
    # arXiv API for AI/ML papers
    try:
        res = requests.get(
            "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending",
            timeout=20)
        if res.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(res.text, "xml")
            for entry in soup.find_all("entry"):
                title = entry.find("title").text.strip().replace("\n", " ") if entry.find("title") else ""
                link = entry.find("id").text.strip() if entry.find("id") else ""
                published = entry.find("published").text[:10] if entry.find("published") else ""
                summary = entry.find("summary").text.strip()[:200] if entry.find("summary") else ""
                authors = ", ".join([a.find("name").text for a in entry.find_all("author")[:3]])
                if title:
                    events.append({"title": title, "link": link,
                        "raw_date_text": published if published else "Recently published",
                        "source": f"arXiv ({authors})", "category": "AI Research",
                        "description": summary})
    except Exception as e:
        print(f"  [WARN] arXiv: {e}")

    # Hugging Face papers
    try:
        res = requests.get("https://huggingface.co/api/daily_papers", headers=HEADERS, timeout=15)
        if res.status_code == 200:
            papers = res.json()
            for paper in papers[:20]:
                p = paper.get("paper", {})
                title = p.get("title", "").strip()
                pid = p.get("id", "")
                link = f"https://huggingface.co/papers/{pid}" if pid else "https://huggingface.co/papers"
                if title:
                    events.append({"title": title, "link": link,
                        "raw_date_text": p.get("publishedAt", "Today")[:10],
                        "source": "Hugging Face Papers", "category": "AI Research",
                        "description": p.get("summary", "")[:200]})
    except Exception as e:
        print(f"  [WARN] HF Papers: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  CONFERENCES
# ═══════════════════════════════════════════════════════════════
def scrape_conferences() -> List[Dict[str, Any]]:
    events = []
    # WikiCFP for AI conferences
    try:
        res = requests.get("http://www.wikicfp.com/cfp/call?conference=artificial%20intelligence&skip=1", headers=HEADERS, timeout=15)
        if res.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(res.text, "html.parser")
            for row in soup.select("table.sortable tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    a_tag = cols[0].find("a")
                    title = a_tag.text.strip() if a_tag else ""
                    link = "http://www.wikicfp.com" + a_tag["href"] if a_tag and a_tag.get("href") else ""
                    deadline = cols[2].text.strip() if len(cols) > 2 else ""
                    if title and len(title) > 3:
                        events.append({"title": title, "link": link,
                            "raw_date_text": deadline if deadline else "Check website",
                            "source": "WikiCFP", "category": "Conference"})
    except Exception as e:
        print(f"  [WARN] WikiCFP: {e}")

    # Curated top conferences
    conf_list = [
        {"title": "NeurIPS 2026", "link": "https://neurips.cc", "source": "NeurIPS"},
        {"title": "ICML 2026", "link": "https://icml.cc", "source": "ICML"},
        {"title": "CVPR 2026", "link": "https://cvpr.thecvf.com", "source": "CVPR"},
        {"title": "AAAI 2026", "link": "https://aaai.org/conference/aaai/aaai-26/", "source": "AAAI"},
        {"title": "ACL 2026", "link": "https://2026.aclweb.org", "source": "ACL"},
        {"title": "ICLR 2026", "link": "https://iclr.cc", "source": "ICLR"},
        {"title": "SIGKDD 2026", "link": "https://kdd.org", "source": "KDD"},
        {"title": "EMNLP 2026", "link": "https://2026.emnlp.org", "source": "EMNLP"},
        {"title": "Google I/O 2026", "link": "https://io.google", "source": "Google"},
        {"title": "Apple WWDC 2026", "link": "https://developer.apple.com/wwdc26/", "source": "Apple"},
        {"title": "AWS re:Invent 2026", "link": "https://reinvent.awsevents.com", "source": "AWS"},
        {"title": "Microsoft Build 2026", "link": "https://build.microsoft.com", "source": "Microsoft"},
    ]
    for c in conf_list:
        events.append({"title": c["title"], "link": c["link"],
            "raw_date_text": "Apply ASAP, rolling admissions", "source": c["source"], "category": "Conference"})
    return events

# ═══════════════════════════════════════════════════════════════
#  AI TECHNOLOGY
# ═══════════════════════════════════════════════════════════════
def scrape_ai_technology() -> List[Dict[str, Any]]:
    events = []
    if not feedparser: return events
    feeds = [
        ("https://blog.google/technology/ai/rss/", "Google AI Blog"),
        ("https://openai.com/blog/rss.xml", "OpenAI Blog"),
        ("https://blogs.microsoft.com/ai/feed/", "Microsoft AI Blog"),
        ("https://ai.meta.com/blog/rss/", "Meta AI Blog"),
    ]
    for url, source in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                published = entry.get("published", "")
                if title and len(title) > 5:
                    events.append({"title": title, "link": link,
                        "raw_date_text": published if published else "Recently",
                        "source": source, "category": "AI Technology",
                        "description": entry.get("summary", "")[:200]})
        except Exception as e:
            print(f"  [WARN] {source}: {e}")

    # Product Hunt AI products
    try:
        res = requests.get("https://www.producthunt.com/topics/artificial-intelligence", headers=HEADERS, timeout=15)
        if res.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(res.text, "html.parser")
            for item in soup.select("[data-test='post-name'], h3")[:15]:
                title = item.get_text(strip=True)
                a = item.find_parent("a") or item.find("a")
                link = "https://www.producthunt.com" + a["href"] if a and a.get("href") else "https://www.producthunt.com"
                if title and len(title) > 3:
                    events.append({"title": title, "link": link,
                        "raw_date_text": "Trending now", "source": "Product Hunt", "category": "AI Technology"})
    except Exception as e:
        print(f"  [WARN] Product Hunt: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  STARTUPS
# ═══════════════════════════════════════════════════════════════
def scrape_startups() -> List[Dict[str, Any]]:
    events = []
    if feedparser:
        feeds = [
            ("https://techcrunch.com/category/startups/feed/", "TechCrunch Startups"),
            ("https://news.crunchbase.com/feed/", "Crunchbase News"),
        ]
        for url, source in feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:12]:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "")
                    if title:
                        events.append({"title": title, "link": link,
                            "raw_date_text": entry.get("published", "Recently"),
                            "source": source, "category": "Startup",
                            "description": entry.get("summary", "")[:200]})
            except Exception as e:
                print(f"  [WARN] {source}: {e}")

    # Y Combinator companies
    curated_startups = [
        {"title": "Y Combinator S26 Applications Open", "link": "https://ycombinator.com/apply", "source": "Y Combinator"},
        {"title": "Techstars 2026 Accelerator Programs", "link": "https://www.techstars.com/accelerators", "source": "Techstars"},
        {"title": "500 Global Batch 36", "link": "https://500.co/accelerator", "source": "500 Global"},
        {"title": "Antler Residency Program 2026", "link": "https://www.antler.co", "source": "Antler"},
        {"title": "NVIDIA Inception Program", "link": "https://www.nvidia.com/en-us/startups/", "source": "NVIDIA"},
    ]
    for s in curated_startups:
        events.append({"title": s["title"], "link": s["link"],
            "raw_date_text": "Apply ASAP, rolling admissions", "source": s["source"], "category": "Startup"})
    return events

# ═══════════════════════════════════════════════════════════════
#  OPEN SOURCE MODELS
# ═══════════════════════════════════════════════════════════════
def scrape_os_models() -> List[Dict[str, Any]]:
    events = []
    try:
        res = requests.get("https://huggingface.co/api/models?sort=downloads&limit=15", headers=HEADERS, timeout=15)
        if res.status_code == 200:
            models = res.json()
            for m in models:
                mid = m.get("id", "")
                if not mid: continue
                events.append({
                    "title": mid,
                    "link": f"https://huggingface.co/{mid}",
                    "raw_date_text": "Trending today",
                    "source": "Hugging Face",
                    "category": "Open Source Models",
                    "description": f"Trending open-source model: {mid}. Downloads: {m.get('downloads', 0)}"
                })
    except Exception as e:
        print(f"  [WARN] Open Source Models: {e}")
    return events

# ═══════════════════════════════════════════════════════════════
#  CURATED FALLBACKS
# ═══════════════════════════════════════════════════════════════
def get_curated_events() -> List[Dict[str, Any]]:
    return [
        {"title": "Google Summer of Code 2026", "link": "https://summerofcode.withgoogle.com",
         "raw_date_text": "Apply ASAP, rolling admissions", "source": "Google", "category": "Internship"},
        {"title": "Microsoft Imagine Cup 2026", "link": "https://imaginecup.microsoft.com",
         "raw_date_text": "Deadline in 12 days", "source": "Microsoft", "category": "Hackathon"},
        {"title": "AWS Cloud Practitioner Workshop", "link": "https://aws.amazon.com/training",
         "raw_date_text": "Register by next week", "source": "AWS Training", "category": "Workshop"},
        {"title": "MLH Global Hack Week", "link": "https://mlh.io",
         "raw_date_text": "Register by next month", "source": "MLH", "category": "Hackathon"},
        {"title": "IIT Bombay Techfest — e-Summit", "link": "https://techfest.org",
         "raw_date_text": "Register by next month", "source": "IIT Bombay", "category": "Conference"},
    ]

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════
def _is_bad_title(title: str) -> bool:
    if not title or len(title) <= 3: return True
    bad = ['menu', 'navigation', 'footer', 'header', 'sign in', 'sign up',
           'login', 'register', 'search', 'filter', 'home', 'about', 'contact', 'faq']
    return title.lower().strip() in bad

def _deduplicate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for item in items:
        key = re.sub(r'[^a-z0-9]', '', item["title"].lower())
        if key not in seen and len(key) > 3:
            seen.add(key)
            unique.append(item)
    return unique

# ═══════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════
def scrape_events() -> List[Event]:
    print("=" * 60)
    print(f"  [Scraper] Heta Full-Spectrum — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Sync sources
    print("\n[1/9] Devfolio API...")
    devfolio_data = scrape_devfolio()
    print(f"  -> {len(devfolio_data)} items")

    print("[2/9] GitHub Internships...")
    github_data = scrape_github_internships()
    print(f"  -> {len(github_data)} items")

    print("[3/9] AI News (RSS)...")
    news_data = scrape_ai_news()
    print(f"  -> {len(news_data)} items")

    print("[4/9] AI Research Papers...")
    research_data = scrape_ai_research()
    print(f"  -> {len(research_data)} items")

    print("[5/9] Conferences...")
    conf_data = scrape_conferences()
    print(f"  -> {len(conf_data)} items")

    print("[6/9] AI Technology...")
    tech_data = scrape_ai_technology()
    print(f"  -> {len(tech_data)} items")

    print("[7/9] Startups...")
    startup_data = scrape_startups()
    print(f"  -> {len(startup_data)} items")

    # Async sources
    print("[8/10] Open Source Models...")
    os_models_data = scrape_os_models()
    print(f"  -> {len(os_models_data)} items")

    print("[9/10] Devpost + MLH + Unstop (Playwright)...")
    async_results = _run_async_scrapers()
    devpost_data = async_results.get("devpost", [])
    mlh_data = async_results.get("mlh", [])
    unstop_data = async_results.get("unstop", [])

    print("[10/10] Curated fallbacks...")
    curated_data = get_curated_events()

    raw = devfolio_data + devpost_data + mlh_data + unstop_data + github_data + \
          news_data + research_data + conf_data + tech_data + startup_data + os_models_data + curated_data

    raw = _deduplicate(raw)

    print(f"\n{'-' * 40}")
    print(f"  Total raw: {len(raw)}")
    print(f"  Hackathons: {len(devfolio_data)+len(devpost_data)+len(mlh_data)+len(unstop_data)}")
    print(f"  Internships: {len(github_data)} | News: {len(news_data)} | Research: {len(research_data)}")
    print(f"  Conferences: {len(conf_data)} | Tech: {len(tech_data)} | Startups: {len(startup_data)}")
    print(f"  OS Models: {len(os_models_data)}")
    print(f"{'-' * 40}\n")

    events: List[Event] = []
    total_raw = len(raw)
    for i, item in enumerate(raw):
        try:
            if i % 10 == 0: print(f"  [AI Agent] Processing item {i}/{total_raw}: {item['title'][:40]}...")
            ai_result = extract_deadline_and_validate(item["raw_date_text"])
            if ai_result["is_valid"]:
                events.append(Event(
                    id=str(uuid.uuid4()), title=item["title"],
                    registration_link=item["link"],
                    registration_deadline=ai_result["deadline_str"],
                    deadline_date=ai_result.get("deadline_date"),
                    priority=ai_result["priority"],
                    source=item.get("source", "Web"),
                    category=item.get("category"),
                    days_left=ai_result.get("days_left"),
                    description=item.get("description"),
                ))
        except Exception as e:
            print(f"  [WARN] Error processing '{item.get('title', '?')}': {e}")

    events.sort(key=lambda x: (x.deadline_date - datetime.now()).days if x.deadline_date else 999)
    print(f"  [OK] Final valid events: {len(events)}")
    print("=" * 60)
    return events


def _run_async_scrapers() -> Dict[str, List[Dict[str, Any]]]:
    results = {"devpost": [], "mlh": [], "unstop": []}
    if not PLAYWRIGHT_AVAILABLE:
        print("  [INFO] Playwright not available, skipping JS sources")
        return results

    async def _gather():
        r = {}
        try:
            r["devpost"] = await scrape_devpost()
            r["mlh"] = await scrape_mlh()
            r["unstop"] = await scrape_unstop()
        except Exception as e:
            print(f"  [WARN] Async error: {e}")
        return r

    try:
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = pool.submit(lambda: asyncio.run(_gather())).result(timeout=90)
        except RuntimeError:
            results = asyncio.run(_gather())
    except Exception as e:
        print(f"  [WARN] Failed async scrapers: {e}")
    return results
