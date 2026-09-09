# PO Exception Triage — UI

Next.js dashboard for the PO exception triage agent.

## Run

1. **Backend** (from `../backend`):
   ```bash
   pip install -r requirements.txt
   copy .env.example .env   # add OPENAI_API_KEY
   uvicorn src.api:app --reload --port 8000
   ```
2. **Frontend** (from here):
   ```bash
   npm install
   copy .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   npm run dev
   ```
3. Open http://localhost:3000

## Test

```bash
npm run test        # unit/component (Vitest)
npm run e2e         # end-to-end (Playwright, network mocked)
npm run typecheck
```

The first `/triage` call downloads the embedding model and builds the SOP index on the
backend; subsequent calls reuse the cache.
