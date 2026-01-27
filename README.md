# PolyDelta

**Crypto Prediction Market Arbitrage Platform**

Track real-time odds discrepancies between Polymarket and traditional bookmakers. Find +EV betting opportunities with AI-powered analysis.

## Features

- **Odds Comparison** - Real-time odds from traditional bookmakers vs Polymarket prices
- **Arbitrage Detection** - Automatic identification of risk-free arbitrage opportunities
- **AI Analysis** - LLM-powered strategy recommendations with Kelly Criterion calculations
- **Multi-Sport Coverage**:
  - FIFA World Cup 2026 Championship
  - NBA Championship & Daily Matches
- **Trading Calculator** - Arbitrage, Kelly, and Net ROI calculators with fee modeling

## Tech Stack

### Frontend (`/web`)
- Next.js 14 (App Router)
- React 18 + TypeScript
- Tailwind CSS
- Prisma ORM
- Clerk Authentication
- Recharts for data visualization

### Backend (`/scraper`)
- Python 3.11+
- PostgreSQL (Railway)
- OpenRouter API (Gemini 2.0 Flash)
- Polymarket Gamma API
- The Odds API

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL database

### Environment Variables

Create `.env` in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# APIs
ODDS_API_KEY=your_odds_api_key
OPENROUTER_API_KEY=your_openrouter_key

# Clerk (in web/.env.local)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_publishable_key
CLERK_SECRET_KEY=your_secret_key
```

### Installation

```bash
# Frontend
cd web
npm install
npx prisma generate
npm run dev

# Scraper
cd scraper
pip install -r requirements.txt
python scraper.py
```

## Project Structure

```
polydelta/
├── web/                    # Next.js frontend
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   └── contexts/      # React contexts
│   └── prisma/            # Database schema
├── scraper/               # Python data scraper
│   ├── scraper.py         # Main scraper
│   └── sports_prompt_builder.py  # AI prompt generation
└── .github/
    └── workflows/         # GitHub Actions (hourly scraper)
```

## Deployment

- **Frontend**: Railway (auto-deploy from GitHub)
- **Database**: Railway PostgreSQL
- **Scraper**: GitHub Actions (hourly cron)

## License

MIT

---

Built with [Claude Code](https://claude.ai/code)
