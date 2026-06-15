# M-Pesa Prompting App

A focused, production-ready web application for triggering M-Pesa STK Push (Lipa Na M-Pesa) payments. Built with a React frontend and a Python serverless backend deployed on Vercel. The customer enters their phone number and an amount, receives a PIN prompt on their phone, and the UI updates in real time when Safaricom confirms the payment — no page refresh needed.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**What it does:** Presents a payment form where a user enters a Safaricom phone number and an amount. On submission the backend calls Safaricom's Daraja STK Push API, which sends a PIN prompt to the customer's phone. The frontend subscribes to the `mpesa_payments` table via Supabase Realtime and navigates to a success or failure screen the moment Safaricom's callback updates the database record — with no polling required.

**Problem it solves:** Wires together the three moving parts of a live STK Push flow — token management, payment initiation, and asynchronous callback handling — into a deployable, end-to-end web app.

**Intended users:** Developers and operators in Kenya who need a working M-Pesa STK Push integration they can deploy and extend.

---

## Features

- **STK Push initiation** — submits a Lipa Na M-Pesa Online payment request to Safaricom's Daraja API
- **Asynchronous callback handling** — receives Safaricom's POST callback, parses the result, and upserts it to the database
- **Real-time payment status** — the frontend uses Supabase Realtime (Postgres `LISTEN`/`NOTIFY`) to detect the callback update and navigate immediately, without polling
- **Redis token caching** — the M-Pesa OAuth access token is cached in Upstash Redis for 55 minutes, avoiding a round-trip to Safaricom on every request
- **Pending record pattern** — a `result_code = -1` placeholder row is written at initiation time so the callback always has a row to `UPDATE` into, even when it arrives in milliseconds
- **Phone number normalisation** — accepts `07XXXXXXXX`, `+2547XXXXXXXX`, or `2547XXXXXXXX` and normalises to the `2547XXXXXXXX` format the API requires
- **QR code placeholder** — a QR card section is present in the UI and flagged in source as pending implementation

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, React Router v7, Vite 8 |
| **Backend** | Python serverless functions (Vercel) |
| **Database** | PostgreSQL via Supabase (psycopg2 on backend, `@supabase/supabase-js` on frontend) |
| **Realtime** | Supabase Realtime (Postgres changes) |
| **Caching** | Upstash Redis (REST API via `upstash-redis`) |
| **HTTP (Python)** | `requests` |
| **Environment** | `python-dotenv` |
| **Build tool** | Vite |
| **Linting** | ESLint 10 with `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh` |
| **Deployment** | Vercel (frontend + Python serverless functions) |
| **External API** | Safaricom Daraja API (M-Pesa) |

> **Note:** `PyJWT` and `bcrypt` are listed in `requirements.txt` but are not currently used. They are retained for a planned authentication layer.

---

## Architecture

```
Browser (React SPA)
        │
        │  POST /api/pay  (fetch to Vercel deployment URL)
        ▼
Vercel Serverless Functions (Python)
        │
        ├── Daraja API (Safaricom)   ← STK Push request
        ├── Upstash Redis            ← access token cache
        └── Supabase (PostgreSQL)    ← writes pending payment record
                │
                │  Safaricom POSTs callback to /api/callback
                ▼
        api/callback.py  → upserts result into mpesa_payments
                │
                │  Supabase Realtime notifies frontend subscriber
                ▼
        Browser navigates to /success or /failure
```

**Payment flow step by step:**

1. The user submits the payment form (phone + amount).
2. The frontend POSTs to `/api/pay`.
3. `api/pay.py` fetches an M-Pesa access token (from Redis cache or Daraja OAuth), calls STK Push, and writes a pending row (`result_code = -1`) to `mpesa_payments`.
4. The frontend receives the `checkout_request_id` and calls `waitForPayment()`, which first checks whether a non-pending result already exists in the table, then subscribes to Supabase Realtime for an `UPDATE` event on that row.
5. The customer enters their M-Pesa PIN on their phone.
6. Safaricom POSTs the result to `/api/callback`.
7. `api/callback.py` upserts the result (receipt number, amount, phone, result code) using `COALESCE` so that fields already saved at initiation are not overwritten with nulls.
8. Supabase Realtime fires, `waitForPayment()` resolves, and the frontend navigates to `/success` (with receipt details) or `/failure`.

---

## Project Structure

```
mpesa-app/
│
├── src/                          # React frontend
│   ├── components/
│   │   ├── Form.jsx              # Payment form — phone, amount, submit
│   │   ├── Header.jsx            # Page header / title
│   │   └── Qrcode.jsx            # QR code card (pending implementation)
│   │
│   ├── pages/
│   │   ├── App.jsx               # Root component — React Router routes
│   │   ├── Payment.jsx           # Main payment page (Form + Header + QR)
│   │   ├── Success.jsx           # Shown after confirmed payment
│   │   ├── Failure.jsx           # Shown after cancelled/failed payment
│   │   └── Loading.jsx           # (currently unused)
│   │
│   ├── styles/
│   │   ├── index.css
│   │   ├── App.css
│   │   └── payment.css
│   │
│   ├── assets/
│   │   ├── greencheck.png        # Success icon
│   │   └── redcross.webp         # Failure icon
│   │
│   └── main.jsx                  # React entry point — mounts BrowserRouter
│
├── api/                          # Python serverless functions (Vercel)
│   ├── pay.py                    # POST /api/pay  — initiates STK Push
│   └── callback.py               # POST /api/callback  — receives Safaricom callback
│
├── lib/                          # Shared Python utilities
│   ├── accesstoken.py            # OAuth token fetch + Upstash Redis caching
│   ├── stkpush.py                # STK Push request builder and sender
│   ├── helpers.py                # (stub — reserved for shared response helpers)
│   └── supabase.js               # Supabase JS client (used by frontend utils)
│
├── utils/
│   └── waitForPayment.js         # Supabase Realtime subscriber — awaits callback result
│
├── public/
│   └── brain.png                 # Favicon
│
├── index.html                    # Vite HTML entry point
├── vite.config.js                # Vite config
├── eslint.config.js              # ESLint configuration
├── package.json                  # JS dependencies and scripts
├── package-lock.json             # Lockfile (commit this)
├── requirements.txt              # Python dependencies
├── vercel.json                   # Vercel build + SPA rewrite config
├── .gitignore
├── CONTRIBUTING.md
├── DOCUMENTATION.md              # Extended Daraja API reference guide
└── LICENSE.md
```

> **Note:** `venv/`, `node_modules/`, `dist/`, and `.env` are auto-generated or secret and are excluded from version control per `.gitignore`. Several local development scripts (`lib/basicstkpush.py`, `api/callbackserver.py`, `api/status.py`) are also gitignored — they may contain hardcoded values and must never be committed.

---

## Installation

### Prerequisites

- Node.js ≥ 18
- Python 3.9+
- A [Safaricom Daraja developer account](https://developer.safaricom.co.ke/) — to obtain API credentials and a shortcode/till number
- A [Supabase](https://supabase.com/) project — for the PostgreSQL database and Realtime subscriptions
- An [Upstash](https://upstash.com/) Redis database — for access token caching
- A [Vercel](https://vercel.com/) account — for deployment and running Python serverless functions locally

### 1. Clone the repository

```bash
git clone https://github.com/RobertTRL/mpesa-app.git
cd mpesa-app
```

### 2. Install JavaScript dependencies

```bash
npm install
```

### 3. Set up Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. See [Environment Variables](#environment-variables) for the full list. There is no `.env.example` file committed — use the table below as your template.

### 5. Start the development server

**Frontend only** (no Python API functions):

```bash
npm run dev
```

**Full stack** (frontend + Python serverless functions via Vercel CLI):

```bash
npm install -g vercel
vercel dev
```

> `vercel dev` is required to run `api/pay.py` and `api/callback.py` locally. `npm run dev` serves only the React frontend.

> **Important:** The frontend currently hardcodes the production Vercel deployment URL (`https://mpesa-app-indol.vercel.app/api/pay`) inside `src/components/Form.jsx`. For local development against `vercel dev`, change this to `http://localhost:3000/api/pay` (or your local Vercel dev port).

---

## Environment Variables

Create a `.env` file at the project root with the following variables. Use Vercel's environment variable settings for production secrets.

### Backend (Python) — required

| Variable | Description |
|---|---|
| `PRODUCTION_CONSUMER_KEY` | Daraja API consumer key from the Safaricom developer portal |
| `PRODUCTION_CONSUMER_SECRET` | Daraja API consumer secret |
| `PRODUCTION_BASE_URL` | Daraja base URL — `https://api.safaricom.co.ke` for production or `https://sandbox.safaricom.co.ke` for sandbox |
| `PRODUCTION_SHORTCODE` | Your M-Pesa business shortcode (paybill number) |
| `PRODUCTION_PASSKEY` | STK Push passkey provided by Safaricom for your shortcode |
| `PRODUCTION_TILL_NUMBER` | Your Buy Goods till number (used as `PartyB` in the STK Push payload) |
| `PRODUCTION_CALLBACK_URL` | Public HTTPS URL where Safaricom will POST STK Push results — must be your Vercel deployment URL + `/api/callback` |
| `DATABASE_URL` | Full PostgreSQL connection string for your Supabase database (e.g. `postgresql://postgres:<password>@<host>:5432/postgres`) |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST endpoint URL |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST auth token |

### Frontend (Vite) — required

These variables must be prefixed with `VITE_` to be exposed to the browser by Vite.

| Variable | Description |
|---|---|
| `VITE_SUPABASE_URL` | Your Supabase project URL (e.g. `https://xyzxyz.supabase.co`) |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase `anon` / publishable key — safe to expose in the frontend |

> ⚠️ **Never commit `.env` to version control.** `.gitignore` already excludes it. The `VITE_SUPABASE_PUBLISHABLE_KEY` is intentionally a public (anon) key — do not substitute the service role key here.

---

## Database Schema

The application uses a single table, `mpesa_payments`, in your Supabase PostgreSQL database. You must create this table manually before running the app.

```sql
CREATE TABLE mpesa_payments (
    id                   SERIAL PRIMARY KEY,
    checkout_request_id  VARCHAR(100) UNIQUE NOT NULL,
    result_code          INTEGER NOT NULL DEFAULT -1,
    result_desc          TEXT,
    amount               NUMERIC(12, 2),
    mpesa_receipt        VARCHAR(50),
    phone                VARCHAR(20),
    created_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mpesa_payments_checkout_id ON mpesa_payments (checkout_request_id);
```

**Column notes:**

- `result_code = -1` is the sentinel value for a pending payment. The backend writes this at initiation time and the frontend filters it out when checking for an existing result.
- `result_code = 0` means payment completed successfully.
- Any other `result_code` (e.g. `1032` = cancelled, `1037` = timed out, `1` = insufficient funds) means the payment failed.
- `mpesa_receipt` is populated only on success — it holds the M-Pesa receipt number shown to the customer.

**Supabase Realtime** must be enabled on this table for the frontend's live payment status to work. In your Supabase dashboard: Database → Replication → `mpesa_payments` → enable for `UPDATE` events.

---

## Usage

### Sandbox testing

1. Register on the [Safaricom Daraja portal](https://developer.safaricom.co.ke/) and create a sandbox app.
2. Set `PRODUCTION_BASE_URL=https://sandbox.safaricom.co.ke` in your `.env`.
3. Use Safaricom's sandbox test credentials:
   - Shortcode: `174379`
   - Passkey: `bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919`
   - Test phone: `254708374149` (only this number works in sandbox)
4. Your callback URL must be publicly accessible over HTTPS — use [ngrok](https://ngrok.com) or deploy to Vercel.
5. Start the app and navigate to the payment form.

### Making a payment

1. Enter a Safaricom phone number (the form accepts `07XXXXXXXX` format).
2. Enter an amount in KES (minimum 1).
3. Click **Send payment**.
4. The customer receives an M-Pesa PIN prompt on their phone.
5. After the customer enters their PIN, Safaricom POSTs the result to your callback URL.
6. The UI navigates to `/success` (showing receipt number, amount, and phone) or `/failure` (showing the reason).

If no callback is received within 60 seconds, `waitForPayment()` times out and shows an error message.

---

## API Reference

Both endpoints are Python files in `api/` and are served as Vercel serverless functions. In production they are available at your Vercel deployment domain.

---

### `POST /api/pay` — Initiate STK Push

Triggers a Lipa Na M-Pesa Online PIN prompt on the customer's phone.

**Request body:**

```json
{
  "phone": "0712345678",
  "amount": 100
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `phone` | string | yes | Any common Kenyan format — normalised to `2547XXXXXXXX` internally |
| `amount` | number | yes | Whole number, minimum 1 (KES) |

The `account_reference` is currently hardcoded to `"BOBTOROITICH"` and `transaction_description` to `"Payment"` in the backend. Update `lib/stkpush.py` to accept these from the request body if needed.

**Response (200 — STK Push accepted):**

```json
{
  "success": true,
  "checkout_request_id": "ws_CO_...",
  "merchant_request_id": "...",
  "response_description": "Success. Request accepted for processing",
  "customer_message": "Success. Request accepted for processing"
}
```

**Response (400 — validation error or Daraja rejection):**

```json
{
  "success": false,
  "error": "phone and amount are required"
}
```

**Response (500 — unexpected error):**

```json
{
  "success": false,
  "error": "..."
}
```

> The endpoint also handles `OPTIONS` (CORS preflight) and returns `Access-Control-Allow-Origin: *` on all responses.

---

### `POST /api/callback` — STK Push Callback

Receives Safaricom's asynchronous result after the customer responds to the PIN prompt. This endpoint is called by Safaricom's servers, not the frontend. It must be publicly accessible over HTTPS.

**Always returns HTTP 200** with `{"ResultCode": 0, "ResultDesc": "Accepted"}` regardless of processing outcome — if this endpoint returns anything other than 200, Safaricom will retry the callback repeatedly.

The handler upserts into `mpesa_payments` using `ON CONFLICT (checkout_request_id) DO UPDATE`, with `COALESCE` ensuring the phone and amount saved at initiation are preserved if the callback omits them (e.g. on a cancelled payment).

---

## Available Scripts

```bash
# Start the Vite frontend dev server (no Python API)
npm run dev

# Build the frontend for production
npm run build

# Preview the production build locally
npm run preview

# Run ESLint
npm run lint

# Full-stack local development (frontend + Python API functions)
vercel dev
```

---

## Deployment

The project is configured for deployment on Vercel. `vercel.json` sets the build command, output directory, and an SPA rewrite rule so that React Router routes (`/success`, `/failure`) are handled client-side.

### Steps

1. Push the repository to GitHub.
2. Import the project in the [Vercel dashboard](https://vercel.com/new).
3. Vercel auto-detects the Vite frontend and the Python functions in `api/`.
4. Add all environment variables from the [Environment Variables](#environment-variables) section in Vercel project settings under **Settings → Environment Variables**.
5. Deploy.

### Callback URL

Set `PRODUCTION_CALLBACK_URL` to your Vercel deployment URL plus `/api/callback`:

```
https://your-project.vercel.app/api/callback
```

Safaricom requires callback URLs to be:
- Publicly accessible (not `localhost`)
- HTTPS only
- Responding within a short timeout (always return 200 immediately)
- Free of the words "mpesa", "safaricom", or similar — Safaricom's system may block such URLs

---

## Known Limitations

- **QR code not implemented.** The `Qrcode.jsx` component renders a card shell with a placeholder comment. No QR generation logic exists yet.
- **No authentication.** There is no login, no JWT validation, and no user accounts. The payment form is fully public. `PyJWT` and `bcrypt` are in `requirements.txt` in anticipation of a future auth layer.
- **Hardcoded production URL.** `src/components/Form.jsx` makes requests to the hardcoded Vercel deployment URL. Local development against `vercel dev` requires manually updating this to `http://localhost:3000/api/pay`.
- **No sandbox/production toggle.** The Python backend connects to whichever Daraja URL is set in `PRODUCTION_BASE_URL`. There is no runtime switch — set the variable appropriately per environment.
- **Account reference is hardcoded.** `lib/stkpush.py` uses `"BOBTOROITICH"` as the account reference. This should be made configurable.
- **No automated tests.** There are no unit tests, integration tests, or test configuration files.
- **No CI/CD pipeline.** There are no GitHub Actions workflows. Deployments go directly from `main` to Vercel.
- **Single branch.** There is no `develop` or feature-branch workflow and no branch protection rules.
- **`lib/helpers.py` is empty.** It exists as a stub for shared response helpers that have not been written yet.
- **Non-commercial license restricts production use.** See [License](#license).

---

## Contributing

This is a personal solo project and is not currently open for code contributions.

You are welcome to:
- **Report bugs** — open a GitHub Issue describing what you expected vs. what happened, including error messages or screenshots.
- **Suggest features** — open a GitHub Issue describing your idea.
- **Fork it** — fork the repository and build your own version, subject to the non-commercial license terms.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## License

This project is licensed under the **MIT License (Non-Commercial)**.

Copyright © 2026 Robert Toroitich.

Permission is granted for personal, educational, and non-commercial use. **Commercial use — including use in a commercial product, by a for-profit organisation, or in any revenue-generating activity — is explicitly prohibited.**

See [LICENSE.md](LICENSE.md) for the full license text.