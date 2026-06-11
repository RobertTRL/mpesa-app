# M-Pesa App

A full-stack web application for integrating and interacting with Safaricom's M-Pesa payment APIs. Built with a React frontend and Python serverless backend deployed on Vercel, the app supports STK Push (Lipa Na M-Pesa), C2B, B2C, B2B, transaction status checks, account balance queries, and payment reversals — all behind a JWT-authenticated user interface.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development](#development)
- [Deployment](#deployment)
- [Security Notes](#security-notes)
- [Known Issues / Limitations](#known-issues--limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**What it does:** This application provides a web-based dashboard for triggering and managing M-Pesa transactions. It abstracts the complexity of Safaricom's Daraja API into a clean React UI backed by Python serverless functions.

**Problem it solves:** Integrating M-Pesa's Daraja API requires handling OAuth token generation, STK Push callbacks, C2B URL registration, B2C disbursements, and more — all while keeping credentials secure. This project packages all of that logic into a deployable, stateful web app.

**Intended users:** Developers, product teams, and fintech operators in Kenya (or anywhere M-Pesa operates) who need a ready-made integration layer or a reference implementation for the Daraja API.

---

## Features

- **STK Push (Lipa Na M-Pesa Online)** — Initiate customer-to-business payments directly from the dashboard
- **STK Push Callback** — Receives and processes Safaricom's asynchronous payment confirmations
- **C2B Registration** — Register confirmation and validation URLs for Customer-to-Business payments
- **C2B Validation & Confirmation** — Handle real-time C2B payment events from Safaricom
- **B2C Payments** — Send money from a business shortcode to individual M-Pesa users
- **B2B Payments** — Business-to-business payment initiation
- **Transaction Status Check** — Query the status of any M-Pesa transaction
- **Account Balance Query** — Check the balance of an M-Pesa shortcode
- **Payment Reversal** — Reverse a completed M-Pesa transaction
- **JWT Authentication** — Login/logout flow protecting all dashboard routes
- **Transaction List** — View a history of payment activity
- **Supabase Persistence** — Transactions and user data stored in a PostgreSQL database via Supabase
- **Redis Caching** — M-Pesa access tokens cached in Upstash Redis to avoid unnecessary OAuth calls

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8 |
| **Backend** | Python (serverless functions on Vercel) |
| **Database** | Supabase (PostgreSQL) |
| **Caching** | Upstash Redis |
| **Authentication** | JWT (`PyJWT`), `bcrypt` password hashing |
| **HTTP (Python)** | `requests` |
| **Environment** | `python-dotenv` |
| **Build Tool** | Vite |
| **Linting** | ESLint 10 with `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh` |
| **Deployment** | Vercel (frontend + Python serverless functions) |
| **External API** | Safaricom Daraja API (M-Pesa) |

---

## Architecture

The application follows a **decoupled frontend/backend architecture** deployed as a single Vercel project:

```
Browser (React SPA)
        │
        │  HTTP requests (via Vite proxy in dev / direct in prod)
        ▼
Vercel Serverless Functions (Python)
        │
        ├── Daraja API (Safaricom M-Pesa)   ← outbound payment requests
        ├── Upstash Redis                    ← access token cache
        └── Supabase (PostgreSQL)            ← transaction & user storage
```

**Frontend (`src/`):** A React single-page application with pages for Login and Dashboard. Components handle the payment form, transaction list, and payment status display. Auth state is managed via React Context. API calls are made via service modules (`auth.js`, `payment.js`).

**Backend (`api/`):** Python files in the `api/` directory are automatically treated as serverless functions by Vercel. Each file corresponds to one endpoint. Shared utilities live in `api/lib/` (`auth.py` for OAuth token management, `helpers.py` for response formatting).

**Auth flow:** The frontend submits credentials to `/api/auth/login`, which validates them against a Supabase user record (bcrypt-hashed passwords) and returns a signed JWT. All subsequent API calls include this JWT as a Bearer token; the Python functions verify it on every request.

**M-Pesa token management:** Rather than calling Safaricom's OAuth endpoint on every request, the backend caches the access token in Upstash Redis with a TTL matching the token's expiry, minimising latency and API rate-limit exposure.

---

## Installation

### Prerequisites

- Node.js ≥ 18
- Python 3.9+
- A [Safaricom Daraja developer account](https://developer.safaricom.co.ke/)
- A [Supabase](https://supabase.com/) project with a PostgreSQL database
- An [Upstash](https://upstash.com/) Redis database
- A [Vercel](https://vercel.com/) account (for deployment) or the Vercel CLI (for local dev with serverless functions)

### 1. Clone the repository

```bash
git clone https://github.com/RobertTRL/mpesa-app.git
cd mpesa-app
```

### 2. Install JavaScript dependencies

```bash
npm install
```

### 3. Set up Python virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in all required values (see [Environment Variables](#environment-variables) below).

### 5. Start the development server

For frontend-only development (no serverless functions):

```bash
npm run dev
```

For full-stack local development (frontend + Python API functions), use the Vercel CLI:

```bash
npm install -g vercel
vercel dev
```

> **Note:** `vercel dev` is required to run the Python serverless functions locally. `npm run dev` alone will only serve the React frontend.

---

## Environment Variables

Create a `.env` file in the project root based on `.env.example`. The following variables are required:

| Variable | Required | Description |
|---|---|---|
| `MPESA_CONSUMER_KEY` | ✅ | Daraja API consumer key from the Safaricom developer portal |
| `MPESA_CONSUMER_SECRET` | ✅ | Daraja API consumer secret from the Safaricom developer portal |
| `MPESA_SHORTCODE` | ✅ | Your M-Pesa business shortcode (paybill or till number) |
| `MPESA_PASSKEY` | ✅ | STK Push passkey provided by Safaricom for your shortcode |
| `MPESA_CALLBACK_URL` | ✅ | Public HTTPS URL where Safaricom will POST STK Push results (e.g. your Vercel deployment URL + `/api/callbacks/stk`) |
| `MPESA_C2B_CONFIRMATION_URL` | ✅ | Public HTTPS URL for C2B payment confirmations |
| `MPESA_C2B_VALIDATION_URL` | ✅ | Public HTTPS URL for C2B payment validation |
| `MPESA_B2C_INITIATOR_NAME` | ✅ | The API operator username for B2C transactions |
| `MPESA_B2C_SECURITY_CREDENTIAL` | ✅ | Base64-encoded, encrypted initiator password for B2C |
| `MPESA_ENVIRONMENT` | ✅ | `sandbox` or `production` — controls which Daraja base URL is used |
| `SUPABASE_URL` | ✅ | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase service role key (keep secret — grants full DB access) |
| `UPSTASH_REDIS_REST_URL` | ✅ | Upstash Redis REST endpoint URL |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ | Upstash Redis REST auth token |
| `JWT_SECRET` | ✅ | A long random string used to sign and verify JWTs |

> ⚠️ **Never commit `.env` to version control.** The `.gitignore` already excludes it. Use Vercel's environment variable settings for production secrets.

---

## Usage

### Sandbox testing

1. Register on the [Safaricom Daraja portal](https://developer.safaricom.co.ke/) and create a test app.
2. Set `MPESA_ENVIRONMENT=sandbox` in your `.env`.
3. Use Safaricom's sandbox test credentials and phone numbers.
4. Start the app with `vercel dev`.
5. Navigate to `http://localhost:3000`, log in, and use the dashboard to initiate a test STK Push.

### Initiating an STK Push

1. Log in with your credentials.
2. On the Dashboard, fill in the payment form: phone number, amount, and account reference.
3. Submit — the backend calls Safaricom's STK Push endpoint and returns a `CheckoutRequestID`.
4. The customer receives a PIN prompt on their phone.
5. Safaricom POSTs the result to your callback URL; the status updates in the UI.

---

## API Documentation

All backend routes are Python serverless functions under `api/`. In production they are available at your Vercel deployment domain. In local dev they run via `vercel dev`.

### Payments

All payment endpoints require `Authorization: Bearer <JWT>` in the request header.

#### `POST /api/pay` — STK Push

Initiate a Lipa Na M-Pesa Online (STK Push) payment.

**Request body:**
```json
{
  "phone": "254712345678",
  "amount": 100,
  "account_ref": "INV001",
  "description": "Payment for invoice"
}
```

**Response (200):**
```json
{
  "MerchantRequestID": "...",
  "CheckoutRequestID": "...",
  "ResponseCode": "0",
  "ResponseDescription": "Success. Request accepted for processing",
  "CustomerMessage": "Success. Request accepted for processing"
}
```

#### `POST /api/callbacks/stk` — STK Push Callback

Receives Safaricom's asynchronous callback after an STK Push. This endpoint must be publicly accessible and registered with Safaricom.

> This endpoint is called by Safaricom's servers, not the frontend.

---

#### `POST /api/c2b/register` — Register C2B URLs

Register confirmation and validation URLs with Safaricom.

#### `POST /api/c2b/validate` — C2B Validation

Called by Safaricom to validate an incoming C2B payment before confirmation.

#### `POST /api/c2b/confirm` — C2B Confirmation

Called by Safaricom to confirm a completed C2B payment.

---

#### `POST /api/b2c` — Business to Customer

Disburse funds from a business shortcode to a mobile number.

**Request body:**
```json
{
  "phone": "254712345678",
  "amount": 500,
  "remarks": "Salary payment",
  "occasion": "Monthly salary"
}
```

#### `POST /api/b2b` — Business to Business

Transfer funds between business shortcodes.

#### `GET /api/status` — Transaction Status

Query the status of a specific M-Pesa transaction.

**Query params:** `?transaction_id=<M-Pesa transaction ID>`

#### `GET /api/balance` — Account Balance

Query the balance of the configured M-Pesa shortcode.

#### `POST /api/reversal` — Transaction Reversal

Reverse a completed M-Pesa transaction.

**Request body:**
```json
{
  "transaction_id": "OEI2AK4Q16",
  "amount": 100,
  "remarks": "Duplicate payment reversal"
}
```

---

## Project Structure

```
mpesa-app/
│
├── src/                          # React frontend
│   ├── components/
│   │   ├── Login.jsx             # Login form component
│   │   ├── Dashboard.jsx         # Main dashboard layout
│   │   ├── PaymentForm.jsx       # STK Push / payment initiation form
│   │   ├── PaymentStatus.jsx     # Displays transaction result/status
│   │   └── TransactionList.jsx   # History of past transactions
│   ├── pages/
│   │   ├── LoginPage.jsx         # Login route page wrapper
│   │   └── DashboardPage.jsx     # Dashboard route page wrapper
│   ├── services/
│   │   ├── auth.js               # Auth API calls (login, logout)
│   │   └── payment.js            # Payment API calls (STK Push, status, etc.)
│   ├── context/
│   │   └── AuthContext.jsx       # React Context for auth state
│   ├── App.jsx                   # Root component, routing
│   └── main.jsx                  # React entry point
│
├── api/                          # Python serverless functions (Vercel)
│   ├── lib/
│   │   ├── auth.py               # M-Pesa OAuth token helper (with Redis caching)
│   │   └── helpers.py            # Shared HTTP response helpers
│   ├── auth/
│   │   ├── login.py              # POST /api/auth/login
│   │   └── logout.py             # POST /api/auth/logout
│   ├── pay.py                    # POST /api/pay (STK Push)
│   ├── callbacks/
│   │   └── stk.py                # POST /api/callbacks/stk (STK Push callback)
│   ├── c2b/
│   │   ├── register.py           # POST /api/c2b/register
│   │   ├── validate.py           # POST /api/c2b/validate
│   │   └── confirm.py            # POST /api/c2b/confirm
│   ├── b2c.py                    # POST /api/b2c
│   ├── b2b.py                    # POST /api/b2b
│   ├── balance.py                # GET  /api/balance
│   └── reversal.py               # POST /api/reversal
│
├── public/
│   └── favicon.ico
│
├── index.html                    # Vite HTML entry point
├── vite.config.js                # Vite config (dev proxy to /api)
├── eslint.config.js              # ESLint configuration
├── package.json                  # JS dependencies and scripts
├── package-lock.json             # Lockfile (commit this)
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for environment variables
├── .gitignore
├── CONTRIBUTING.md
├── DOCUMENTATION.md              # Extended internal documentation
├── LICENSE.md
└── README.md
```

> **Note:** `vercel.json`, `venv/`, `node_modules/`, `dist/`, and `.env` are either auto-generated or excluded from version control per `.gitignore`.

---

## Development

### Available scripts

```bash
# Start the Vite frontend dev server (frontend only, no API)
npm run dev

# Build the frontend for production
npm run build

# Preview the production build locally
npm run preview

# Run ESLint
npm run lint

# Full-stack local development (frontend + Python serverless functions)
vercel dev
```

### Adding a new API endpoint

1. Create a new `.py` file under `api/` (or a subdirectory).
2. Export an HTTP handler function (see existing endpoints for the pattern).
3. Import shared utilities from `api/lib/auth.py` and `api/lib/helpers.py`.
4. Test locally with `vercel dev`.

### Testing

> ⚠️ **No automated test suite is currently present in this repository.** There are no unit tests, integration tests, or test configuration files. See [Known Issues / Limitations](#known-issues--limitations).

For manual testing:
- Use the Safaricom Sandbox environment and its provided test credentials.
- Use tools like [Postman](https://www.postman.com/) or `curl` to call API endpoints directly.

---

## Deployment

The project is designed for **zero-config deployment on Vercel**.

### Steps

1. Push the repository to GitHub.
2. Import the project in the [Vercel dashboard](https://vercel.com/new).
3. Vercel auto-detects the Vite frontend and the Python functions in `api/`.
4. Add all environment variables from [Environment Variables](#environment-variables) in the Vercel project settings under **Settings → Environment Variables**.
5. Deploy — Vercel handles building the frontend and deploying the Python functions.

### Callback URL requirements

Safaricom requires that callback/confirmation/validation URLs be:
- Publicly accessible (not `localhost`)
- HTTPS only
- Responding within a short timeout

Set `MPESA_CALLBACK_URL` to your Vercel deployment URL, e.g.:

```
https://your-project.vercel.app/api/callbacks/stk
```

Register C2B URLs **once** by hitting `POST /api/c2b/register` after deployment.

---

## Security Notes

- **All secrets are environment variables.** The `.gitignore` excludes `.env`. Never hardcode credentials.
- **Supabase service role key** grants full database access — treat it like a root password. Do not expose it to the frontend.
- **JWT secret** must be a long, randomly generated string (e.g. `openssl rand -hex 32`). Rotating it invalidates all existing sessions.
- **bcrypt** is used for password hashing (`bcrypt` library). Passwords are never stored in plaintext.
- **M-Pesa B2C Security Credential** must be encrypted with Safaricom's public certificate before use. Refer to the Daraja documentation for the encryption process.
- **Callback endpoints** (`/api/callbacks/stk`, `/api/c2b/validate`, `/api/c2b/confirm`) are publicly accessible by design (Safaricom calls them). Consider validating the source IP against Safaricom's known IP ranges in production.
- **HTTPS is enforced** by Vercel in production. Never disable this.
- Some files are explicitly excluded from the repository via `.gitignore` (`lib/basicstkpush.py`, `api/callbackserver.py`, `api/status.py`) — this may indicate local development scripts with hardcoded values; ensure these are never committed.

---

## Known Issues / Limitations

- **No automated tests.** There are no unit, integration, or end-to-end tests. This is a significant gap for a payment application — errors in credential handling or API response parsing could go undetected.
- **No `vercel.json` in the repository.** The project structure references `vercel.json` in the README tree but the file was not present in the repository at the time of this writing. Vercel's auto-detection may work without it, but explicit configuration is recommended for production (routing rules, Python runtime version pinning).
- **No `.env.example` file committed.** The project structure documents `.env.example` as safe to commit, but it was not present in the repository. New contributors cannot know which variables are needed without reading the code. Add this file.
- **`api/status.py` is gitignored.** The transaction status endpoint is excluded from version control. This means the `/api/status` route will not work after a fresh clone.
- **No React Router.** The project uses React 19 without a visible routing library in `package.json`. Navigation between Login and Dashboard pages may rely on conditional rendering in `App.jsx` rather than proper URL-based routing. Consider adding `react-router-dom` for bookmarkable URLs and browser-history support.
- **No error boundary or global error handling** is apparent in the frontend dependencies.
- **Single branch (`main`).** There is no `develop` or feature-branch workflow, and no branch protection rules are configured.
- **No CI/CD pipeline.** There are no GitHub Actions workflows. Deployments go directly from `main` to Vercel with no automated quality gate.
- **Non-commercial license restricts production use.** See [License](#license).

---

## Contributing

This is a personal solo project and is **not currently open for code contributions**.

You are welcome to:
- **Report bugs** — open a GitHub Issue with a description of what you expected vs. what happened, including any error messages or screenshots.
- **Suggest features** — open a GitHub Issue describing your idea.
- **Fork it** — fork the repository and build your own version, subject to the non-commercial license terms.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guidelines.

---

## License

This project is licensed under the **MIT License (Non-Commercial)**.

Copyright © 2026 Robert Toroitich.

Permission is granted for personal, educational, and non-commercial use. **Commercial use — including use in a commercial product, by a for-profit organisation, or in any revenue-generating activity — is explicitly prohibited.**

See [LICENSE.md](LICENSE.md) for the full license text.