# Recursive Domain Video Crawler

A modern, production-ready, asynchronous web application that recursively crawls websites (restricted to the starting domain), automates dynamic page loading via Playwright, monitors network traffic for streaming media assets, and registers all discovered video sources in a responsive dashboard.

---

## Technical Stack

- **Backend**: Python 3.11, FastAPI, Playwright (Async API), SQLAlchemy, BeautifulSoup4, SQLite (with WAL mode enabled)
- **Frontend**: React, Vite, TailwindCSS, TanStack Table (v8), Recharts, Lucide Icons
- **Real-Time Communication**: WebSockets for streaming crawler logs and progress statistics
- **Orchestration**: Docker, Docker Compose, Nginx (for serving frontend and reverse proxying backend)

---

## Project Structure

```text
crawler/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py   # SQLAlchemy session & SQLite WAL configuration
│   │   ├── models.py     # Database schema (Sessions, Pages, Videos, Logs)
│   │   ├── schemas.py    # Pydantic serialization schemas
│   │   ├── crawler.py    # Asynchronous BFS Playwright crawler
│   │   └── main.py       # FastAPI application endpoints & WebSockets
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CrawlForm.jsx      # Crawl configuration form
│   │   │   ├── StatusPanel.jsx    # Real-time counter and elapsed time panel
│   │   │   ├── StatsPanel.jsx     # Distribution charts and format counters
│   │   │   ├── LogPanel.jsx       # Terminal console streaming websocket logs
│   │   │   └── ResultsTable.jsx   # Searchable and sortable TanStack table
│   │   ├── App.jsx                # Layout orchestrator and state coordinator
│   │   ├── index.css
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf                 # Nginx proxy for reverse proxying /crawl and /ws
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
└── docker-compose.yml
```

---

## Crawler Features & Mechanics

1. **Domain Restriction**: Only crawls URLs whose host matches the starting URL's hostname (or its subdomains). External links are logged as `[SKIP_EXTERNAL]` and ignored.
2. **Duplicate Detection**: Normalizes URLs by converting hostnames/protocols to lowercase, stripping fragments (`#section`), and trimming trailing slashes so paths like `/about/` and `/about` are treated identically.
3. **Dynamic Page Automation**: Playwright navigates to pages and waits for `domcontentloaded` followed by an extra `networkidle` delay to allow JavaScript-loaded elements to render.
4. **Video Detection Channels**:
   - **DOM Scraping**: Evaluates `<video>` tags and `<source>` sub-tags for media URLs.
   - **Network Traffic Monitoring**: Listens to active outgoing requests during page loading for extensions like `.mp4`, `.m3u8` (HLS), `.mpd` (DASH), `.webm`, `.mov`, and `.m4v`.
   - **Anchor Scraping**: Inspects hyperlink tags (`<a href="...">`) to see if they link directly to static media formats.
5. **Worker Concurrency**: Spawns up to 10 lightweight concurrent workers sharing a browser instance using separate isolation contexts.

---

## Run with Docker Compose (Recommended)

Docker Compose configures Nginx, mounts database volumes for persistence, and provisions all Playwright dependencies inside the backend container.

### Prerequisites
- Docker and Docker Compose installed.

### Steps
1. Navigate to the project root:
   ```bash
   cd /Users/prasetiyo-valortek/Downloads/crawler
   ```

2. Spin up the containers:
   ```bash
   docker compose up --build
   ```

3. Open your browser and navigate to:
   - **Dashboard**: [http://localhost:8080](http://localhost:8080)
   - **FastAPI API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Local Development (Without Docker)

You can run the frontend and backend servers locally on your machine.

### 1. Backend Setup
Make sure you have Python 3.10+ installed.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browser components and system dependencies:
   ```bash
   playwright install chromium
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
Make sure you have Node.js 18+ installed.

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   - Vite is configured to host on [http://localhost:3000](http://localhost:3000) and proxy API requests to port `8000`.

---

## API Endpoints

- **Start Crawl** (`POST /crawl/start`): Starts a crawl session in the background.
  - Body: `{ "url": "https://example.com", "depth": 3, "max_pages": 100, "concurrent_workers": 5 }`
- **Status & Stats** (`GET /crawl/status`): Returns live page counters, speed, and format breakdown for the current/latest crawl.
- **Results** (`GET /crawl/results`): Fetches the list of discovered video resources.
- **Crawl Logs** (`GET /crawl/logs`): Fetches the latest 100 logs.
- **Export JSON** (`GET /crawl/export/json`): Triggers a download of the results as a JSON file.
- **Export CSV** (`GET /crawl/export/csv`): Triggers a download of the results as a CSV file.
- **WebSockets** (`WS /ws/crawl`): Broadcasts log additions and stats updates in real time.
