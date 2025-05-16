TradeEasy MVP Product Requirements Document (PRD)

Purpose:
This PRD details requirements for TradeEasy’s Backend (Shaun) and Frontend (Ruckshi) development phases in Cursor. It will guide both AI-assisted development agents in implementing the MVP as specified.

1. Project Overview

Product: TradeEasy—real-time sentiment analytics platform for equities, FX, crypto, and commodities

Scope: Web‑only MVP with hourly news ingestion, sentiment scoring, and a Bloomberg‑style dashboard

Team:

Shaun: Backend engineer (finance expert + developer) using FastAPI for ingestion, storage, NLP, and APIs

Ruckshi: Frontend engineer (full‑stack) using Next.js + Aceternity UI for web interface

Timeline: 8 weeks; this PRD covers initial setup and core feature definitions

2. Backend Requirements (Shaun)

2.1 Technical Stack

Framework: FastAPI (Python 3.11)

Database: PostgreSQL

Libraries: SQLAlchemy, Uvicorn, feedparser, newspaper3k, python-dotenv, transformers (FinBERT)

Deployment: Docker (uvicorn entrypoint)

2.2 Core Features & Endpoints

Health Check

Endpoint: GET /health

Response: { "status": "ok" }

RSS Ingestion

Scheduler: Hourly via APScheduler/Cron

Functionality: Fetch from RSS_SOURCES, parse items, extract full article text, dedupe, store

Article Storage

Model: Article(id, source, title, content, published_at)

Duplication Check: Hash link or content

Sentiment Analysis

Preprocessing: Lowercase, strip HTML, tokenize, remove stop‑words

Lexicon Score: Loughran‑McDonald dictionary

Transformer Score: FinBERT via HuggingFace pipeline

Sentiment API

POST /api/sentiment/article: returns lexicon + FinBERT scores for input text

GET /api/sentiment/latest?asset={symbol}: returns latest sentiment metrics

Search

GET /api/search?q={query}: full‑text search over articles.content, returns list with sentiment tags

Sentiment History

GET /api/history?asset={symbol}&range={timespan}: returns time‑series aggregate scores

Watchlists & Alerts

Models: Watchlist(user_id, asset), Alert(user_id, asset, threshold, direction, created_at)

Endpoints: CRUD for watchlists, alerts; background check to insert triggered alerts

Real‑Time Updates

WebSocket /ws/sentiment: broadcast new aggregates

Fallback: /api/sentiment/stream?since=timestamp

2.3 Data Model & Schema

Article: id (UUID), source (string), title, content (text), published_at (datetime)

Sentiment: id, article_id (FK), lexicon_score (float), finbert_score (float)

SentimentAggregate: id, asset (string), timestamp (datetime), avg_score (float)

Watchlist: id, user_id, asset

Alert: id, user_id, asset, threshold, direction (above/below), triggered_at

2.4 Non‑Functional Requirements

Latency: Sentiment API ≤200 ms per request

Scalability: Support 10 k RSS items/hour; horizontal scaling via Docker

Reliability: ≥99.5% uptime in pilot

Security: Sanitize inputs, JWT auth for protected endpoints, rate limiting

3. Frontend Requirements (Ruckshi)

3.1 Technical Stack

Framework: Next.js (TypeScript)

UI Library: Aceternity UI (React + Tailwind CSS)

Charts: TradingView Charting Library or Chart.js

Real‑Time: WebSocket or polling fallback

3.2 Pages & Components

Layout & Navigation

<Navbar>: top bar with brand and nav links

<Sidebar>: asset categories (Equities, FX, Crypto, Commodities)

Dashboard

Components:

<SentimentGauge asset="AAPL" score={0.12}>

Top news carousel <Carousel items={...}>

Market table: list of assets with sentiment & price columns

Search

<SearchBar>, <SearchResults>: show articles, sentiment badges, link to asset pages

Watchlist

<WatchlistTable>: rows of user assets; real‑time sentiment, price; remove button

Alerts

<AlertForm>: select asset, threshold, direction

<AlertLog>: list of triggered alerts with timestamp; mark-as-read

Asset Detail

Header: asset name, live sentiment gauge, current price

Chart: sentiment history line chart with range selector

News List: recent articles with titles and scores

3.3 UI Behavior & Interactions

Dark Theme: default; toggle UI class .dark globally

Responsive Grid: 4-column layout on desktop; collapse to 1–2 columns below 768 px

Real‑Time Updates: subscribe to WS; animate gauge and table cells on change

Routing: Next.js dynamic routing for /asset/[symbol]

3.4 Environment & Integration

Env Vars: NEXT_PUBLIC_API_URL=http://localhost:8000/api

Local Dev: npm run dev -- --port 3000

Cursor Run Command: same; set port binding

3.5 Non‑Functional Requirements

Performance: Initial page load ≤1 s; WS updates render within 300 ms

Accessibility: WCAG AA compliance; semantic HTML, ARIA labels on dynamic components

Testing: React Testing Library for components; achieve ≥80% coverage

