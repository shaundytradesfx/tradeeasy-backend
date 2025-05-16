Week 1: Architecture & Setup

Shaun (Backend)

Initialize tradeeasy-backend repo & Dockerfile
Create Python venv; install FastAPI, Uvicorn, SQLAlchemy, feedparser, newspaper3k, python-dotenv
Scaffold directory structure: app/main.py, app/database.py, app/models.py, app/routers/ingestion.py, tests/
Define .env.example with DATABASE_URL, RSS_SOURCES
Write GET /health endpoint in main.py
Ruckshi (Frontend)

Initialize tradeeasy-ui repo via create-next-app with TypeScript, ESLint, Tailwind
Install Aceternity UI (npm install @aceternity/ui)
Configure tailwind.config.js for dark theme (primary, accent, bg colors)
Scaffold page structure under src/pages: dashboard.tsx, search.tsx, watchlist.tsx, alerts.tsx, asset/[symbol].tsx
Create Layout.tsx (Navbar + Sidebar) and wrap in _app.tsx
Week 2: Ingestion & UI Skeleton

Shaun

Collect & validate 10 RSS URLs for equities, FX, crypto, commodities
Implement rss_ingest.py: fetch & parse feeds (title, link, published date) with feedparser
Stub newspaper3k integration to extract full article text
Define SQLAlchemy models: Article(id, source, title, content, published_at)
Write DAO functions to upsert articles and dedupe
Ruckshi

Build basic routes and navigation with Aceternity’s <Navbar> and <Container>
Create UI “stub” components for Dashboard, Search, Watchlist, Alerts, Asset Detail (placeholder cards)
Point each page at stubbed JSON endpoints (e.g. /api/health, /api/articles)
Week 3: NLP Pipeline & Dashboard Prototype

Shaun

Implement nlp/preprocess.py: lowercase, strip HTML, tokenize, remove stop‑words (spaCy)
Load Loughran‑McDonald lexicon; compute lexicon-based score
Integrate FinBERT via HuggingFace (ProsusAI/finbert) for transformer-based scoring
Expose POST /api/sentiment/article endpoint returning both scores
Write unit tests for preprocessing and scoring
Ruckshi

Build <SentimentGauge> component using Aceternity’s gauge or Card component
Create Dashboard prototype: grid of <SentimentGauge> for AAPL, EUR/USD, BTC, Gold with dummy data
Install charting library (Chart.js or TradingView) and stub a “sentiment over time” line chart
Week 4: Ingestion Scaling & Core Features

Shaun

Schedule hourly ingestion with APScheduler; implement error handling & retries
Persist full articles in Postgres; log metrics (fetched, saved, errors)
Compute hourly aggregates: SentimentAggregate(asset, timestamp, avg_score)
Build GET /api/history?asset={symbol}&range={timespan} endpoint
Define Watchlist & Alert models; implement background check to generate alerts
Ruckshi

Build Search UI: <SearchBar> + <SearchResults> calling GET /api/search?q=
Build Watchlist UI: <WatchlistTable> showing symbol, sentiment, price; “Add/Remove” buttons
Build Alerts UI: <AlertForm> (asset, threshold, direction) + <AlertLog>
Week 5: Real‑Time Integration

Shaun

Add WebSocket /ws/sentiment to broadcast new aggregates
Provide REST fallback /api/sentiment/stream?since=
Ensure alerts are emitted in real time when thresholds crossed
Ruckshi

In Dashboard, hook <SentimentGauge> and <WatchlistTable> to WebSocket feed; animate updates
In Alerts log, subscribe to WS for new alerts and display instantly
Finalize Asset Detail page: live gauge + “View History” chart pulling from /api/history
Week 6: Polish & Documentation

Shaun

Implement JWT‑based auth for watchlists/alerts (login stub for “demo” user)
Add DB indexes on asset, timestamp for faster queries
Optimize text-processing (batch inference, async I/O)
Ruckshi

Refine UI styling: typography, spacing, responsive breakpoints (Tailwind)
Add tooltips/ARIA labels for accessibility; ensure WCAG AA compliance
Write React Testing Library tests for core components (target ≥ 80% coverage)
Week 7: QA & Load Testing

Shaun

Expand pytest suite; cover ingestion edge cases and all API endpoints
Load-test search and history endpoints (e.g. Locust for ≥100 req/s)
Integrate Prometheus/Grafana for ingestion & API monitoring
Ruckshi

Conduct manual cross-browser QA (Chrome, Firefox, Edge)
Test responsiveness on desktops & tablets
Integrate Sentry for frontend error tracking
Week 8: Launch Preparation & Release

Shaun

Final code review & merge; ensure ≥90% test coverage
Deploy backend to production (Docker on AWS/GCP); configure env vars
Monitor first 48 h (uptime, ingestion success rate)
Ruckshi

Final deploy of Next.js app to production (Vercel or Docker host)
Update API URL to production in NEXT_PUBLIC_API_URL
Publish user & developer docs; share Postman collection
Lead launch demo for pilot partners; collect feedback
