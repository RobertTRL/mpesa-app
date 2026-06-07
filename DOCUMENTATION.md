# The Complete M-Pesa Daraja API Integration Guide
**From Sandbox to Production — A Practical, Production-Focused Course**

*Guide version: 2024 | For the latest Daraja documentation, visit [developer.safaricom.co.ke](https://developer.safaricom.co.ke)*

> **Who this guide is for:** Developers with basic programming knowledge (Python or JavaScript) who want to integrate M-Pesa payments into real-world applications. No prior Daraja experience needed.

---

## Table of Contents

0. [Quick-Start Tutorial — Your First Daraja Script](#0-quickstart)
1. [Introduction to M-Pesa Daraja API](#1-introduction)
2. [Setting Up a Safaricom Developer Account](#2-setup)
3. [Authentication](#3-authentication)
4. [Understanding Daraja API Architecture](#4-architecture)
5. [STK Push Integration](#5-stk-push)
6. [Callback Handling](#6-callbacks)
7. [C2B Integration](#7-c2b)
8. [B2C Integration](#8-b2c)
9. [Transaction Status API](#9-transaction-status)
10. [Account Balance API](#10-account-balance)
11. [Reversal API](#11-reversals)
12. [Database Design](#12-database)
13. [Security Best Practices](#13-security)
14. [Production Deployment](#14-production)
15. [Building a Complete Real-World Project](#15-project)
16. [Advanced Topics](#16-advanced)
17. [Common Errors and Troubleshooting](#17-errors)
18. [Production Readiness Checklist](#18-checklist)

---

## 0. Quick-Start Tutorial — Your First Daraja Script {#0-quickstart}

Before diving into architecture, design patterns, and production concerns, this section gives you a single working script that demonstrates the full STK Push flow from first principles. The goal is logic clarity — no classes, no abstraction layers, just a linear sequence of API calls you can read top to bottom.

### What this script does

1. Reads your credentials from environment variables
2. Fetches an OAuth access token
3. Generates the STK Push password
4. Sends an STK Push request to a phone number
5. Prints the result

You will need:
- A Safaricom developer account (see Section 2)
- Python 3.8+ and the `requests` library (`pip install requests`)
- A publicly accessible callback URL (use [ngrok](https://ngrok.com) during development)

### The script

```python
# mpesa_quickstart.py
# A minimal, linear script showing the full STK Push flow.
# No classes, no abstraction — just the logic.

import os
import base64
import requests
from datetime import datetime

# ─── Step 1: Configuration ────────────────────────────────────────────────────
# Load from environment variables — never hardcode credentials.
# Run: export MPESA_CONSUMER_KEY=xxx MPESA_CONSUMER_SECRET=xxx etc.

CONSUMER_KEY    = os.environ["MPESA_CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["MPESA_CONSUMER_SECRET"]
SHORTCODE       = os.environ.get("MPESA_SHORTCODE", "174379")
PASSKEY         = os.environ.get("MPESA_PASSKEY",
                    "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
CALLBACK_URL    = os.environ["MPESA_CALLBACK_URL"]   # must be a public HTTPS URL

# Sandbox base URL. Change to https://api.safaricom.co.ke for production.
BASE_URL = "https://sandbox.safaricom.co.ke"

# In sandbox, use the official test number — your real number won't work.
TEST_PHONE = "254708374149"


# ─── Step 2: Get an OAuth access token ────────────────────────────────────────
# Daraja uses OAuth 2.0 Client Credentials. You encode your key and secret
# as Base64(key:secret) and send them as HTTP Basic Auth.

print("Step 1: Fetching access token...")

credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

token_response = requests.get(
    f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
    headers={"Authorization": f"Basic {encoded_credentials}"},
    timeout=30,
)

# Raise an exception immediately if the request failed (e.g., wrong credentials).
token_response.raise_for_status()

token_data = token_response.json()
access_token = token_data["access_token"]

print(f"  ✓ Token received (expires in {token_data['expires_in']}s)")


# ─── Step 3: Generate the STK Push password ───────────────────────────────────
# The password proves you know the passkey without sending it in plain text.
# Formula: Base64(Shortcode + Passkey + Timestamp)
# The timestamp is included so the password changes every minute, preventing
# replayed requests from being reused.

print("Step 2: Generating password...")

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")   # e.g. "20240115143023"
raw_password = SHORTCODE + PASSKEY + timestamp
password = base64.b64encode(raw_password.encode("utf-8")).decode("utf-8")

print(f"  ✓ Timestamp: {timestamp}")
print(f"  ✓ Password:  {password[:20]}... (truncated)")


# ─── Step 4: Send the STK Push request ────────────────────────────────────────
# This triggers a PIN prompt on the customer's phone.
# The API responds immediately with a CheckoutRequestID — NOT with the
# payment result. The payment result arrives later via your callback URL.

print("Step 3: Sending STK Push request...")

stk_payload = {
    "BusinessShortCode": SHORTCODE,
    "Password":          password,
    "Timestamp":         timestamp,
    "TransactionType":   "CustomerPayBillOnline",
    "Amount":            1,                  # KES 1 for testing
    "PartyA":            TEST_PHONE,         # who is paying
    "PartyB":            SHORTCODE,          # who is being paid (your shortcode)
    "PhoneNumber":       TEST_PHONE,         # who gets the PIN prompt
    "CallBackURL":       CALLBACK_URL,       # where Daraja posts the result
    "AccountReference":  "TEST-001",         # shown to the customer (max 12 chars)
    "TransactionDesc":   "Test payment",     # brief description (max 13 chars)
}

stk_response = requests.post(
    f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
    json=stk_payload,
    headers={
        "Authorization":  f"Bearer {access_token}",
        "Content-Type":   "application/json",
    },
    timeout=30,
)

stk_data = stk_response.json()

print(f"  Raw response: {stk_data}")


# ─── Step 5: Interpret the response ───────────────────────────────────────────
# ResponseCode "0" means Daraja accepted your request and sent the prompt
# to the phone. It does NOT mean the payment succeeded.

if stk_data.get("ResponseCode") == "0":
    checkout_id = stk_data["CheckoutRequestID"]
    print("\n✅ STK Push sent successfully!")
    print(f"   CheckoutRequestID: {checkout_id}")
    print(f"   Customer message:  {stk_data.get('CustomerMessage')}")
    print()
    print("   What happens next:")
    print("   1. The test phone receives a PIN prompt (in sandbox, this is simulated).")
    print("   2. After the customer responds, Daraja POSTs the result to your CALLBACK_URL.")
    print("   3. Your callback endpoint reads the result and updates your database.")
    print(f"\n   Save this ID to match the callback: {checkout_id}")
else:
    print("\n❌ STK Push failed.")
    print(f"   Error: {stk_data.get('errorMessage') or stk_data.get('ResponseDescription')}")
    print(f"   Code:  {stk_data.get('errorCode') or stk_data.get('ResponseCode')}")


# ─── Step 6: (Optional) Query the status of the request ──────────────────────
# If your callback URL is not yet set up, you can poll the status manually.
# In production you would not poll — you rely on the callback.

print("\nStep 4: Querying STK Push status (optional — useful when callback isn't set up)...")

if stk_data.get("ResponseCode") == "0":
    # Re-generate password — timestamp may have changed
    timestamp2 = datetime.now().strftime("%Y%m%d%H%M%S")
    raw_password2 = SHORTCODE + PASSKEY + timestamp2
    password2 = base64.b64encode(raw_password2.encode("utf-8")).decode("utf-8")

    query_payload = {
        "BusinessShortCode": SHORTCODE,
        "Password":          password2,
        "Timestamp":         timestamp2,
        "CheckoutRequestID": checkout_id,
    }

    query_response = requests.post(
        f"{BASE_URL}/mpesa/stkpushquery/v1/query",
        json=query_payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        timeout=30,
    )

    query_data = query_response.json()
    result_code = query_data.get("ResultCode")

    STATUS_MEANINGS = {
        "0":    "Success — payment completed",
        "1":    "Insufficient balance",
        "1032": "Request cancelled by user",
        "1037": "Timeout — user did not respond",
        "2001": "Wrong PIN entered",
    }

    meaning = STATUS_MEANINGS.get(str(result_code), f"Unknown code: {result_code}")
    print(f"  ResultCode: {result_code} → {meaning}")
    print(f"  ResultDesc: {query_data.get('ResultDesc')}")
```

### How to run it

```bash
# Install the only dependency
pip install requests

# Set your credentials (get these from developer.safaricom.co.ke)
export MPESA_CONSUMER_KEY="your_consumer_key"
export MPESA_CONSUMER_SECRET="your_consumer_secret"
export MPESA_CALLBACK_URL="https://your-public-url.example.com/callback"

# Run
python mpesa_quickstart.py
```

### What to look for in the output

```
Step 1: Fetching access token...
  ✓ Token received (expires in 3599s)
Step 2: Generating password...
  ✓ Timestamp: 20240115143023
  ✓ Password:  MTc0Mzc5YmZiMjc5Zj... (truncated)
Step 3: Sending STK Push request...
  Raw response: {'MerchantRequestID': '...', 'CheckoutRequestID': 'ws_CO_...', 'ResponseCode': '0', ...}

✅ STK Push sent successfully!
   CheckoutRequestID: ws_CO_191220191020363925
   Customer message:  Success. Request accepted for processing.
   ...
```

If you see a `ResponseCode` of `"0"`, the flow is working. The rest of this guide explains how to wrap this logic into a maintainable production system.

---

## 1. Introduction to M-Pesa Daraja API {#1-introduction}

### What is M-Pesa?

M-Pesa (M for mobile, Pesa for money in Swahili) is a mobile money service originally launched by Safaricom in Kenya in 2007. It allows users to deposit, withdraw, transfer money, pay for goods and services, access credit and savings — all via a mobile phone. As of 2024, M-Pesa processes over $314 billion in transactions annually and has more than 51 million active users across 7 countries.

### What is Daraja?

Daraja (Swahili for "bridge") is Safaricom's official API platform that bridges your application to the M-Pesa payment ecosystem. Before Daraja, integrating M-Pesa required direct agreements, physical visits, and complex setups. Daraja democratized access — any developer can now register, get API credentials, and start integrating M-Pesa payments in hours.

Daraja is available at: [https://developer.safaricom.co.ke](https://developer.safaricom.co.ke)

### How Daraja Works Within the M-Pesa Ecosystem

```
┌─────────────────────────────────────────────────────────────────────┐
│                     M-PESA ECOSYSTEM                                │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────────────┐  │
│  │  Safaricom   │────▶│  M-Pesa Core │────▶│   Customer Phone   │  │
│  │  Network     │     │  Platform    │     │   (USSD / App)     │  │
│  └──────────────┘     └──────┬───────┘     └────────────────────┘  │
│                              │                                      │
│                    ┌─────────▼──────────┐                          │
│                    │   Daraja API       │                          │
│                    │  (Your Gateway)    │                          │
│                    └─────────┬──────────┘                          │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
              ┌────────────────▼──────────────────┐
              │         YOUR APPLICATION           │
              │  (Web / Mobile / Backend Service)  │
              └───────────────────────────────────┘
```

When a customer pays via M-Pesa on your platform:

1. Your backend sends a signed API request to Daraja
2. Daraja forwards it to the M-Pesa Core Platform
3. The customer receives a prompt on their phone (for STK Push) or confirms on USSD
4. M-Pesa processes the transaction
5. Daraja sends a callback to your specified URL with the result
6. Your backend processes the result and updates your database

### Common Business Use Cases

**1. STK Push (Lipa na M-Pesa Online)**

Used when you want to trigger a payment prompt on the customer's phone from your application. The customer sees "Pay KES X to [Business Name]?" and enters their PIN. Used by e-commerce sites, subscription services, and ticketing platforms.

*Example:* A customer checks out on Jumia, enters their phone number, and receives an M-Pesa PIN prompt immediately.

**2. Customer-to-Business (C2B)**

Used when customers initiate payment themselves — typically by sending money to a Paybill or Buy Goods number. You register callback URLs that Daraja calls when a payment arrives.

*Example:* A customer sends money to Paybill 522200 with account number INV-001. Your system receives a callback and marks invoice INV-001 as paid.

**3. Business-to-Customer (B2C)**

Used when your business sends money to customers — for salary disbursements, refunds, prize money, or welfare distributions.

*Example:* An insurance company sends a claim settlement of KES 50,000 directly to a customer's M-Pesa.

**4. Transaction Status**

Used to query the status of any previous transaction. Critical for reconciliation when callbacks fail or timeout.

*Example:* Your server crashed and you missed 20 callbacks. You use Transaction Status to check each transaction and reconcile.

**5. Account Balance**

Used to check your M-Pesa business account balance programmatically — useful for financial dashboards or triggering low-balance alerts.

**6. Reversals**

Used to reverse a completed transaction — for refunds, erroneous charges, or fraud response.

### Daraja API Request Flow

```
┌──────────────┐    1. POST /oauth/v1/generate    ┌─────────────────┐
│  Your        │ ─────────────────────────────────▶│                 │
│  Backend     │                                   │  Daraja API     │
│  Server      │ ◀─────────────────────────────────│  Gateway        │
└──────┬───────┘    2. Returns access_token        └────────┬────────┘
       │                                                    │
       │  3. POST /mpesa/stkpush/v1/processrequest          │
       │     Headers: Authorization: Bearer {token}         │
       │ ─────────────────────────────────────────────────▶ │
       │                                                     │
       │ ◀─────────────────────────────────────────────────  │
       │  4. Response: {CheckoutRequestID, ResponseCode}     │
       │                                                     │
       │                              ┌──────────────────────▼─────┐
       │                              │  M-Pesa Core               │
       │                              │  - Sends USSD push to phone │
       │                              │  - Customer enters PIN      │
       │                              │  - Transaction processes    │
       │                              └──────────────────────┬─────┘
       │                                                      │
       │  5. POST /your-callback-url                          │
       │     (async, may come 5–30 seconds later)             │
       │ ◀─────────────────────────────────────────────────  │
       │                                                     │
       │  6. Your backend processes and stores result        │
       ▼
┌──────────────┐
│  Database    │
│  (Updated)   │
└──────────────┘
```

### Sandbox vs Production Environments

| Feature | Sandbox | Production |
|---|---|---|
| URL Base | `https://sandbox.safaricom.co.ke` | `https://api.safaricom.co.ke` |
| Real money | No — simulated | Yes — real transactions |
| Phone numbers | Test numbers provided | Real Safaricom numbers |
| Approval needed | No — instant | Yes — business approval process |
| Callbacks | Delivered to your URL | Delivered to **pre-registered** URLs only |
| Shortcodes | Test shortcodes (e.g., 174379) | Your approved business shortcode |
| Callback URLs | Any public HTTPS URL | Must be pre-registered in the Daraja portal |

> **Key point:** Sandbox and Production have the same API structure. Changing environments is mostly a matter of swapping base URLs and credentials — with one critical exception: in production, all callback URLs must be pre-registered with Safaricom through the portal before they will receive traffic. See Section 14 for details.

---

## 2. Setting Up a Safaricom Developer Account {#2-setup}

### Step 1: Create a Developer Account

1. Navigate to [https://developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Click "Sign Up"
3. Fill in: First Name, Last Name, Email address, Phone number (a working Safaricom number), Password
4. Verify your email via the link sent to your inbox
5. Log in to the Developer Portal

### Step 2: Create Your First Application

Once logged in:

1. Click "My Apps" in the top navigation
2. Click "Add a New App"
3. Fill in:
   - **App Name:** e.g., "ShopMax Payments" (descriptive, business-relevant)
   - **Description:** Briefly describe what your app does
   - Select the APIs you need (you can select all for development)
   - Tick: Lipa na M-Pesa Sandbox, M-Pesa Express, Customer To Business (C2B), Business To Customer (B2C), etc.
4. Click "Create App"

> **Critical production constraint — plan before you apply:** In the sandbox you can tick all APIs on one app. In production, **C2B and B2C cannot share the same shortcode**. If your shortcode was approved for C2B (receiving payments from customers), Safaricom will not allow it to also make outgoing B2C payments, and vice versa. STK Push (Lipa na M-Pesa Online) can share an app with C2B but not with B2C. Additionally, B2C and B2B require **separate whitelisting** by Safaricom's support team even after go-live — selecting them in the portal is not sufficient. Contact `apisupport@safaricom.co.ke` or call 2222 to request activation. Discovering this constraint late in a project is one of the most common causes of delayed launches.

### Step 3: Obtain Your Credentials

After creating the app, you'll see a detail page with:

```
Consumer Key:     xxxxxxxxxxxxxxxxxxxxxxxxxxx
Consumer Secret:  xxxxxxxxxxxxxxxxxxxxxxxxxxx
```

These are your API keys — treat them like passwords.

- The **Consumer Key** identifies your application
- The **Consumer Secret** is used to generate an access token
- Together they form Basic Auth credentials: `Base64(ConsumerKey:ConsumerSecret)`

### Step 4: Accessing Sandbox Test Credentials

In the Developer Portal, you'll find:

```
Sandbox Shortcode:  174379
Test MSISDN:        254708374149  (the only phone number that works in sandbox)
Initiator Name:     testapi
Passkey:            bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
```

> **Important:** These sandbox values are publicly documented by Safaricom for testing purposes only. Your production shortcode, passkey, and initiator credentials will be entirely different values assigned to your business during the go-live approval process. Never use sandbox values in production.

### Step 5: Understanding Environment Variables

Never hardcode credentials in your source code. Use environment variables:

```bash
# .env file (never commit this to git — add .env to .gitignore)
MPESA_CONSUMER_KEY=your_consumer_key_here
MPESA_CONSUMER_SECRET=your_consumer_secret_here
MPESA_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://yourdomain.com/callbacks/mpesa
MPESA_ENV=sandbox   # or "production"
```

---

## 3. Authentication {#3-authentication}

### OAuth Overview

Daraja uses OAuth 2.0 with the Client Credentials grant type. This means:

1. You send your Consumer Key and Consumer Secret to the token endpoint
2. You receive a short-lived access token (valid for 1 hour)
3. You include this token in the `Authorization` header of all subsequent API calls

```
Consumer Key + Consumer Secret
        │
        ▼  (Base64 encoded, sent via HTTPS)
  /oauth/v1/generate?grant_type=client_credentials
        │
        ▼
  { access_token: "abc123xyz", expires_in: "3599" }
        │
        ▼
  Authorization: Bearer abc123xyz
```

### Generating Access Tokens

**Using cURL**

```bash
# Encode credentials
CREDENTIALS=$(echo -n "ConsumerKey:ConsumerSecret" | base64)

# Request token
curl -X GET \
  "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" \
  -H "Authorization: Basic ${CREDENTIALS}"

# Response:
# {
#   "access_token": "SGWcJPtNtYNPGm1udzEjORxEqwRk",
#   "expires_in": "3599"
# }
```

> **Note:** Daraja uses GET for token generation (unusual for OAuth but required here).

**Using Python**

```python
import requests
import base64
import os
from datetime import datetime, timedelta

class DarajaAuth:
    """
    Handles OAuth authentication with Daraja API.
    Implements token caching to avoid unnecessary requests.
    """

    def __init__(self):
        self.consumer_key    = os.environ.get("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")
        self.environment     = os.environ.get("MPESA_ENV", "sandbox")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        # Token cache
        self._token        = None
        self._token_expiry = None

    def _encode_credentials(self) -> str:
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        return base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    def _is_token_valid(self) -> bool:
        if self._token is None or self._token_expiry is None:
            return False
        # 5-minute buffer prevents using a token that's about to expire mid-request
        return datetime.now() < (self._token_expiry - timedelta(minutes=5))

    def get_access_token(self) -> str:
        """Get a valid access token, using cache if available."""
        if self._is_token_valid():
            return self._token
        return self._fetch_new_token()

    def _fetch_new_token(self) -> str:
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

        try:
            response = requests.get(
                url,
                headers={"Authorization": f"Basic {self._encode_credentials()}"},
                timeout=30,   # Always set timeouts
            )
            response.raise_for_status()
            data = response.json()

            self._token = data["access_token"]
            self._token_expiry = datetime.now() + timedelta(seconds=int(data["expires_in"]))

            return self._token

        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Daraja API. Check your internet connection.")
        except requests.exceptions.Timeout:
            raise Exception("Daraja API request timed out. Try again.")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Daraja authentication failed: {e.response.text}")
        except KeyError:
            raise Exception("Unexpected response format from Daraja. Check your credentials.")
```

**Using Node.js**

```javascript
const axios = require('axios');

class DarajaAuth {
  constructor() {
    this.consumerKey    = process.env.MPESA_CONSUMER_KEY;
    this.consumerSecret = process.env.MPESA_CONSUMER_SECRET;
    this.environment    = process.env.MPESA_ENV || 'sandbox';

    this.baseUrl = this.environment === 'production'
      ? 'https://api.safaricom.co.ke'
      : 'https://sandbox.safaricom.co.ke';

    this._token       = null;
    this._tokenExpiry = null;
  }

  _encodeCredentials() {
    return Buffer.from(`${this.consumerKey}:${this.consumerSecret}`).toString('base64');
  }

  _isTokenValid() {
    if (!this._token || !this._tokenExpiry) return false;
    const bufferMs = 5 * 60 * 1000;
    return Date.now() < (this._tokenExpiry - bufferMs);
  }

  async getAccessToken() {
    if (this._isTokenValid()) return this._token;
    return this._fetchNewToken();
  }

  async _fetchNewToken() {
    const url = `${this.baseUrl}/oauth/v1/generate?grant_type=client_credentials`;

    try {
      const response = await axios.get(url, {
        headers: { 'Authorization': `Basic ${this._encodeCredentials()}` },
        timeout: 30000,
      });

      this._token       = response.data.access_token;
      const expiresInMs = parseInt(response.data.expires_in, 10) * 1000;
      this._tokenExpiry = Date.now() + expiresInMs;

      return this._token;
    } catch (error) {
      if (error.response) {
        throw new Error(`Daraja auth failed: ${JSON.stringify(error.response.data)}`);
      } else if (error.request) {
        throw new Error('No response from Daraja API. Check connectivity.');
      } else {
        throw new Error(`Auth request error: ${error.message}`);
      }
    }
  }
}

module.exports = new DarajaAuth();
```

### Token Expiration and Best Practices

Tokens expire in 3599 seconds (≈1 hour). Common pitfalls:

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Request new token for every API call | Unnecessary overhead, can hit rate limits | Cache with expiry check |
| Never refresh the token | API calls fail after 1 hour | Implement expiry checking |
| Hardcode token in code | Security nightmare | Always fetch programmatically |
| Share one token across processes | Race conditions in multi-process apps | Use a shared cache (Redis) |

**For production, use Redis for token caching:**

```python
import redis
import json

class DarajaAuthWithRedis:
    REDIS_KEY = "daraja:access_token"

    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        # ... other setup ...

    def get_access_token(self) -> str:
        # Try Redis cache first
        cached = self.redis_client.get(self.REDIS_KEY)
        if cached:
            return json.loads(cached)["token"]

        # Fetch new token under a Redis lock to prevent race conditions
        # in multi-process deployments (e.g., Gunicorn with multiple workers)
        lock_key = "daraja:token_lock"
        lock = self.redis_client.set(lock_key, "1", nx=True, ex=10)  # 10-second lock

        if not lock:
            # Another process is fetching — wait briefly and retry cache
            import time
            time.sleep(0.5)
            cached = self.redis_client.get(self.REDIS_KEY)
            if cached:
                return json.loads(cached)["token"]

        try:
            token = self._fetch_new_token()

            # Store in Redis with TTL (55 minutes — expires 5 min before Daraja expiry)
            self.redis_client.setex(
                self.REDIS_KEY,
                3300,
                json.dumps({"token": token})
            )
            return token
        finally:
            self.redis_client.delete(lock_key)
```

---

## 4. Understanding Daraja API Architecture {#4-architecture}

### API Endpoint Structure

All Daraja endpoints follow this pattern:

```
{base_url}/{service}/{version}/{operation}

Examples:
POST https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest
POST https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl
POST https://sandbox.safaricom.co.ke/mpesa/b2c/v1/paymentrequest
GET  https://sandbox.safaricom.co.ke/oauth/v1/generate
```

### Callback URLs — The Most Critical Concept

Callbacks are how Daraja notifies you of transaction outcomes. Since M-Pesa transactions are asynchronous (the customer has to pick up their phone and enter a PIN), Daraja cannot return the result in the original HTTP response. Instead:

1. Your initial API call returns immediately with a `CheckoutRequestID`
2. Minutes later (or seconds), Daraja makes an HTTP POST to your callback URL
3. Your callback endpoint receives the result and updates your database

**Critical requirements for callback URLs:**

- Must be HTTPS (self-signed certificates won't work in production)
- Must be publicly accessible (not localhost)
- Must return HTTP 200 within 10 seconds or Daraja marks it as failed
- Must be idempotent (Daraja may retry callbacks)
- **In production:** must be pre-registered in the Daraja portal (see Section 14)
- **URL naming restriction:** Do not include the words "mpesa", "m-pesa", "safaricom", or any variant in your callback URLs — Safaricom's system filters these out and will block the URL. `https://yourdomain.com/payments/callback` is fine; `https://yourdomain.com/mpesa/callback` is not.
- **ngrok and public URL testers** (mockbin, requestbin) are blocked in production. Use a real domain.

**For development, use ngrok to expose localhost:**

```bash
# Install ngrok, then expose your local port 5000
ngrok http 5000

# ngrok gives you a URL like:
# https://abc123.ngrok.io → forwards to http://localhost:5000
```

### Common Response Codes

| Code | Meaning | Action |
|---|---|---|
| `0` | Success | Process the result |
| `1` | Insufficient funds | Notify customer |
| `17` | Risk management limit | Customer needs to contact Safaricom |
| `1032` | Request cancelled by user | Log and notify |
| `1037` | Timeout — no user input | Prompt retry |
| `2001` | Wrong PIN entered | Customer should try again |
| `1001` | Temporarily unable to process | Retry after a delay |
| `500.001.1001` | Subscriber locked in another STK session | Wait 30 seconds, retry |

---

## 5. STK Push Integration {#5-stk-push}

STK Push (Sim Toolkit Push) is the most commonly used Daraja feature. It triggers a payment prompt directly on the customer's phone.

### How It Works — First Principles

```
Your App          Daraja API          M-Pesa          Customer Phone
   │                  │                  │                  │
   │─── POST ────────▶│                  │                  │
   │  (payment req)   │                  │                  │
   │◀── 200 OK ───────│                  │                  │
   │  CheckoutID      │──── Forward ────▶│                  │
   │                  │                  │──── USSD Push ──▶│
   │                  │                  │                  │ (popup appears)
   │                  │                  │◀─── PIN Input ───│
   │                  │                  │                  │
   │                  │                  │  (processes txn) │
   │                  │◀──── Result ─────│                  │
   │◀─── Callback ────│                  │                  │
   │  (POST to your   │                  │                  │
   │   callback URL)  │                  │                  │
```

### Required Parameters

| Parameter | Description | Example |
|---|---|---|
| `BusinessShortCode` | Your M-Pesa shortcode | `174379` |
| `Password` | Base64(ShortCode + Passkey + Timestamp) | *(generated)* |
| `Timestamp` | Format: YYYYMMDDHHmmss | `20240115143023` |
| `TransactionType` | `CustomerPayBillOnline` or `CustomerBuyGoodsOnline` | `CustomerPayBillOnline` |
| `Amount` | Amount in KES, whole number | `100` |
| `PartyA` | Customer phone number in format 2547XXXXXXXX | `254708374149` |
| `PartyB` | Your shortcode again | `174379` |
| `PhoneNumber` | Same as PartyA | `254708374149` |
| `CallBackURL` | Your HTTPS callback URL | `https://example.com/callback` |
| `AccountReference` | Reference shown to customer (max 12 chars) | `Order-001` |
| `TransactionDesc` | Brief description (max 13 chars) | `Order Payment` |

> **Truncation warning:** Safaricom silently truncates `AccountReference` beyond 12 characters and `TransactionDesc` beyond 13 characters. Customers will see the truncated version. Validate these lengths in your code before sending.

### Password Generation — Explained

The STK password is a security hash that proves you know the passkey without transmitting it directly:

```
Password = Base64( ShortCode + Passkey + Timestamp )
```

```python
import base64
from datetime import datetime

shortcode = "174379"
passkey   = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

# Timestamp in required format
timestamp    = datetime.now().strftime("%Y%m%d%H%M%S")  # e.g. "20240115143023"
raw_password = shortcode + passkey + timestamp

password = base64.b64encode(raw_password.encode()).decode("utf-8")
```

The timestamp is included so the password changes every minute, making intercepted requests unreusable.

### Complete Python Implementation

```python
import requests
import base64
import os
from datetime import datetime
from typing import Dict, Any


class STKPush:
    """Handles M-Pesa STK Push (Lipa na M-Pesa Online) requests."""

    def __init__(self, auth_client):
        self.auth         = auth_client
        self.shortcode    = os.environ.get("MPESA_SHORTCODE")
        self.passkey      = os.environ.get("MPESA_PASSKEY")
        self.callback_url = os.environ.get("MPESA_CALLBACK_URL")
        self.environment  = os.environ.get("MPESA_ENV", "sandbox")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

    def _generate_password(self) -> tuple[str, str]:
        timestamp  = datetime.now().strftime("%Y%m%d%H%M%S")
        raw_string = f"{self.shortcode}{self.passkey}{timestamp}"
        password   = base64.b64encode(raw_string.encode("utf-8")).decode("utf-8")
        return password, timestamp

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to 2547XXXXXXXX format."""
        phone = phone.strip().replace(" ", "")
        if phone.startswith("+"): phone = phone[1:]
        if phone.startswith("0"): phone = "254" + phone[1:]

        if not phone.startswith("254") or len(phone) != 12:
            raise ValueError(f"Invalid phone number: {phone}. Expected format: 254XXXXXXXXX")
        return phone

    def initiate(
        self,
        phone_number: str,
        amount: int,
        account_reference: str,
        transaction_description: str = "Payment"
    ) -> Dict[str, Any]:
        """
        Initiate an STK Push payment request.

        Args:
            phone_number: Customer's phone (any common format)
            amount: Amount in KES (whole number, min 1)
            account_reference: Your order/invoice reference (max 12 chars)
            transaction_description: Brief description (max 13 chars)
        """
        if amount < 1:
            raise ValueError("Amount must be at least KES 1")
        if len(account_reference) > 12:
            raise ValueError("AccountReference must be 12 characters or fewer")
        if len(transaction_description) > 13:
            raise ValueError("TransactionDesc must be 13 characters or fewer")

        normalized_phone      = self._normalize_phone(phone_number)
        password, timestamp   = self._generate_password()
        access_token          = self.auth.get_access_token()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "TransactionType":   "CustomerPayBillOnline",
            "Amount":            amount,
            "PartyA":            normalized_phone,
            "PartyB":            self.shortcode,
            "PhoneNumber":       normalized_phone,
            "CallBackURL":       self.callback_url,
            "AccountReference":  account_reference,
            "TransactionDesc":   transaction_description,
        }

        try:
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
                timeout=30,
            )
            data = response.json()

            if data.get("ResponseCode") == "0":
                return {
                    "success":              True,
                    "checkout_request_id":  data["CheckoutRequestID"],
                    "merchant_request_id":  data["MerchantRequestID"],
                    "response_description": data["ResponseDescription"],
                    "customer_message":     data["CustomerMessage"],
                }
            else:
                return {
                    "success": False,
                    "error":   data.get("ResponseDescription", "Unknown error"),
                    "raw":     data,
                }

        except requests.exceptions.Timeout:
            raise Exception("STK Push request timed out.")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Safaricom API.")

    def query_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """Query the status of a pending STK Push request."""
        password, timestamp = self._generate_password()
        access_token        = self.auth.get_access_token()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        response = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        return response.json()
```

### Complete Node.js Implementation

```javascript
const axios  = require('axios');
const dayjs  = require('dayjs');  // npm install dayjs

class STKPush {
  constructor(authClient) {
    this.auth        = authClient;
    this.shortcode   = process.env.MPESA_SHORTCODE;
    this.passkey     = process.env.MPESA_PASSKEY;
    this.callbackUrl = process.env.MPESA_CALLBACK_URL;
    this.environment = process.env.MPESA_ENV || 'sandbox';

    this.baseUrl = this.environment === 'production'
      ? 'https://api.safaricom.co.ke'
      : 'https://sandbox.safaricom.co.ke';
  }

  _generatePassword() {
    const timestamp = dayjs().format('YYYYMMDDHHmmss');
    const raw       = `${this.shortcode}${this.passkey}${timestamp}`;
    const password  = Buffer.from(raw).toString('base64');
    return { password, timestamp };
  }

  _normalizePhone(phone) {
    phone = phone.trim().replace(/\s/g, '');
    if (phone.startsWith('+')) phone = phone.slice(1);
    if (phone.startsWith('0')) phone = '254' + phone.slice(1);
    if (!phone.startsWith('254') || phone.length !== 12) {
      throw new Error(`Invalid phone number: ${phone}`);
    }
    return phone;
  }

  async initiate(phoneNumber, amount, accountReference, transactionDesc = 'Payment') {
    if (amount < 1)                    throw new Error('Amount must be at least KES 1');
    if (accountReference.length > 12)  throw new Error('AccountReference max 12 chars');
    if (transactionDesc.length > 13)   throw new Error('TransactionDesc max 13 chars');

    const phone               = this._normalizePhone(phoneNumber);
    const { password, timestamp } = this._generatePassword();
    const token               = await this.auth.getAccessToken();

    const payload = {
      BusinessShortCode: this.shortcode,
      Password:          password,
      Timestamp:         timestamp,
      TransactionType:   'CustomerPayBillOnline',
      Amount:            amount,
      PartyA:            phone,
      PartyB:            this.shortcode,
      PhoneNumber:       phone,
      CallBackURL:       this.callbackUrl,
      AccountReference:  accountReference,
      TransactionDesc:   transactionDesc,
    };

    try {
      const response = await axios.post(
        `${this.baseUrl}/mpesa/stkpush/v1/processrequest`,
        payload,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type':  'application/json',
          },
          timeout: 30000,
        }
      );

      const data = response.data;

      if (data.ResponseCode === '0') {
        return {
          success:             true,
          checkoutRequestId:   data.CheckoutRequestID,
          merchantRequestId:   data.MerchantRequestID,
          responseDescription: data.ResponseDescription,
          customerMessage:     data.CustomerMessage,
        };
      }
      return { success: false, error: data.ResponseDescription, rawResponse: data };

    } catch (error) {
      if (error.response) throw new Error(`STK Push failed: ${JSON.stringify(error.response.data)}`);
      throw error;
    }
  }
}

module.exports = STKPush;
```

### Understanding STK Push Responses

**Initial response** (synchronous — comes immediately):

```json
{
  "MerchantRequestID": "29115-34620561-1",
  "CheckoutRequestID": "ws_CO_191220191020363925",
  "ResponseCode": "0",
  "ResponseDescription": "Success. Request accepted for processing",
  "CustomerMessage": "Success. Request accepted for processing"
}
```

`ResponseCode: "0"` means Daraja accepted the request — **not** that the payment succeeded.

**Callback** (asynchronous — arrives on your callback URL):

```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          { "Name": "Amount",              "Value": 100.00 },
          { "Name": "MpesaReceiptNumber",  "Value": "NLJ7RT61SV" },
          { "Name": "TransactionDate",     "Value": 20191219102115 },
          { "Name": "PhoneNumber",         "Value": 254708374149 }
        ]
      }
    }
  }
}
```

**Failed payment callback:**

```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 1032,
      "ResultDesc": "Request cancelled by user"
    }
  }
}
```

> **Note:** Failed callbacks have **no** `CallbackMetadata` field. Your parsing code must handle both cases.

---

## 6. Callback Handling {#6-callbacks}

### Why Callbacks Are Necessary

M-Pesa transactions are human-in-the-loop — a real person must pick up their phone, read the prompt, and enter their PIN. This takes 5 seconds to several minutes. HTTP requests can't stay open that long, so Daraja uses a webhook pattern:

1. Your server sends a payment request, gets a `CheckoutRequestID`
2. Your server returns to doing other work
3. Minutes later, Daraja calls your server with the result
4. Your server receives this callback and updates the database

### Callback Payload Structure

```
POST /callbacks/mpesa   (your callback endpoint)
Content-Type: application/json

{
  "Body": {                           ← Top-level wrapper
    "stkCallback": {                  ← STK-specific wrapper
      "MerchantRequestID": "...",     ← Your internal ID
      "CheckoutRequestID": "...",     ← ID from the initial request
      "ResultCode": 0,                ← 0 = success, anything else = failure
      "ResultDesc": "...",            ← Human-readable result
      "CallbackMetadata": {           ← ONLY present on SUCCESS
        "Item": [
          {"Name": "Amount",             "Value": 100.00},
          {"Name": "MpesaReceiptNumber", "Value": "ABC123"},
          {"Name": "TransactionDate",    "Value": 20240115143059},
          {"Name": "PhoneNumber",        "Value": 254712345678}
        ]
      }
    }
  }
}
```

### Processing the Callback

```python
def parse_stk_callback(payload: dict) -> dict:
    """
    Parse an STK Push callback payload into a clean dictionary.
    Handles both success and failure cases.
    """
    callback_data = payload.get("Body", {}).get("stkCallback", {})

    result_code         = callback_data.get("ResultCode")
    merchant_request_id = callback_data.get("MerchantRequestID")
    checkout_request_id = callback_data.get("CheckoutRequestID")
    result_desc         = callback_data.get("ResultDesc")

    result = {
        "success":             result_code == 0,
        "result_code":         result_code,
        "result_desc":         result_desc,
        "merchant_request_id": merchant_request_id,
        "checkout_request_id": checkout_request_id,
        "amount":              None,
        "mpesa_receipt":       None,
        "transaction_date":    None,
        "phone_number":        None,
    }

    # Metadata only present on success
    if result_code == 0:
        items    = callback_data.get("CallbackMetadata", {}).get("Item", [])
        metadata = {item["Name"]: item.get("Value") for item in items}

        result["amount"]           = metadata.get("Amount")
        result["mpesa_receipt"]    = metadata.get("MpesaReceiptNumber")
        result["transaction_date"] = metadata.get("TransactionDate")
        result["phone_number"]     = str(metadata.get("PhoneNumber"))

    return result
```

### Flask Callback Endpoint

```python
from flask import Flask, request, jsonify
import logging
from datetime import datetime

app    = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route("/callbacks/mpesa/stk", methods=["POST"])
def stk_callback():
    """
    Receives STK Push payment callbacks from Daraja.

    CRITICAL REQUIREMENTS:
    1. Must return HTTP 200 within 10 seconds
    2. Must handle duplicate callbacks (idempotency)
    3. Always return 200 — even if your processing fails
       (otherwise Daraja retries indefinitely)
    """
    try:
        payload = request.get_json(force=True)

        if not payload:
            logger.warning("Received empty callback body")
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        # Validate payload schema before processing
        if "Body" not in payload or "stkCallback" not in payload.get("Body", {}):
            logger.warning(f"Malformed callback payload: {payload}")
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        logger.info(f"STK Callback received: {payload}")

        parsed = parse_stk_callback(payload)
        save_transaction_result(parsed)

        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    except Exception as e:
        logger.error(f"Error processing STK callback: {e}", exc_info=True)
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


def save_transaction_result(parsed: dict):
    """Save parsed callback to database with idempotency protection."""
    from database import db, Transaction

    transaction = Transaction.query.filter_by(
        checkout_request_id=parsed["checkout_request_id"]
    ).first()

    if not transaction:
        logger.warning(f"Callback for unknown checkout ID: {parsed['checkout_request_id']}")
        return

    # Idempotency: don't update if already completed
    if transaction.status in ("completed", "failed"):
        logger.info(f"Duplicate callback for {parsed['checkout_request_id']} — ignoring")
        return

    if parsed["success"]:
        transaction.status           = "completed"
        transaction.mpesa_receipt    = parsed["mpesa_receipt"]
        transaction.amount_confirmed = parsed["amount"]
        transaction.completed_at     = datetime.utcnow()
        fulfill_order(transaction.order_id)
    else:
        transaction.status         = "failed"
        transaction.failure_reason = parsed["result_desc"]
        transaction.failed_at      = datetime.utcnow()

    db.session.commit()
    logger.info(f"Transaction {transaction.id} updated: {transaction.status}")
```

### FastAPI Callback Endpoint

```python
from fastapi import FastAPI, Request, BackgroundTasks
import logging

app    = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/callbacks/mpesa/stk")
async def stk_callback(request: Request, background_tasks: BackgroundTasks):
    """
    FastAPI version — BackgroundTasks allows returning 200 immediately
    while processing continues, critical for Daraja's 10-second timeout.
    """
    # Capture body before sending response
    try:
        payload = await request.json()
    except Exception:
        logger.warning("Could not parse callback JSON")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    # Add processing to background (non-blocking)
    background_tasks.add_task(process_stk_callback, payload)

    # Return immediately
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


async def process_stk_callback(payload: dict):
    try:
        parsed = parse_stk_callback(payload)
        await save_transaction_result_async(parsed)
    except Exception as e:
        logger.error(f"Background callback processing failed: {e}", exc_info=True)
```

### Express.js Callback Endpoint

```javascript
const express = require('express');
const router  = express.Router();
const logger  = require('./logger');
const db      = require('./database');

router.post('/callbacks/mpesa/stk', async (req, res) => {
  // Capture body BEFORE sending response
  const payload = req.body;

  // Return 200 immediately
  res.status(200).json({ ResultCode: 0, ResultDesc: 'Accepted' });

  // Process asynchronously AFTER responding
  try {
    if (!payload?.Body?.stkCallback) {
      logger.warn('Invalid STK callback structure received');
      return;
    }

    // Validate payload schema
    const callback = payload.Body.stkCallback;
    if (typeof callback.ResultCode === 'undefined' || !callback.CheckoutRequestID) {
      logger.warn('Callback missing required fields');
      return;
    }

    const { ResultCode, CheckoutRequestID, ResultDesc } = callback;

    const transaction = await db.Transaction.findOne({
      where: { checkoutRequestId: CheckoutRequestID }
    });

    if (!transaction) {
      logger.warn(`No transaction found for CheckoutRequestID: ${CheckoutRequestID}`);
      return;
    }

    if (transaction.status === 'completed' || transaction.status === 'failed') {
      logger.info(`Duplicate callback for ${CheckoutRequestID} — skipping`);
      return;
    }

    if (ResultCode === 0) {
      const items = callback.CallbackMetadata?.Item || [];
      const meta  = Object.fromEntries(items.map(i => [i.Name, i.Value]));

      await transaction.update({
        status:          'completed',
        mpesaReceipt:    meta.MpesaReceiptNumber,
        amountConfirmed: meta.Amount,
        completedAt:     new Date(),
      });

      await fulfillOrder(transaction.orderId);
      logger.info(`Payment completed: ${meta.MpesaReceiptNumber}`);
    } else {
      await transaction.update({
        status:        'failed',
        failureReason: ResultDesc,
        failedAt:      new Date(),
      });
      logger.info(`Payment failed (${ResultCode}): ${ResultDesc}`);
    }
  } catch (error) {
    logger.error('Callback processing error:', error);
  }
});

module.exports = router;
```

> **Key principle:** Always send HTTP 200 before processing. Capture the request body into a variable before the response is sent. If your database is slow and you process first, Daraja's 10-second timeout may expire, causing retries and duplicate processing.

---

## 7. C2B Integration {#7-c2b}

Customer-to-Business (C2B) is used when customers initiate payments themselves using a Paybill or Buy Goods (Till) number — without an STK push from your side.

### How C2B Works

```
Customer                Safaricom Network          Daraja               Your Server
   │                          │                      │                      │
   │── Dials *334# ──────────▶│                      │                      │
   │── Paybill: 522200 ──────▶│                      │                      │
   │── Account: INV-001 ──────▶│                      │                      │
   │── Amount: 5000 ──────────▶│                      │                      │
   │── PIN ──────────────────▶│                      │                      │
   │                          │── Transaction ──────▶│                      │
   │                          │                      │── POST /validate ──▶│
   │                          │                      │◀─ 200 Accept/Reject  │
   │                          │                      │── POST /confirm ────▶│
   │◀── SMS Confirmation ──── │                      │◀─ 200 OK             │
```

### Step 1: Register Your Callback URLs

Before receiving C2B payments, you must register your callback URLs with Safaricom. This is a one-time setup (but can be updated).

> **Sandbox C2B callback reliability:** C2B callbacks in the sandbox are notoriously unreliable — many developers report receiving them only 30–40% of the time, or not at all. This is a known Safaricom sandbox limitation, not a bug in your code. If you cannot get C2B callbacks working in sandbox despite a correct integration, deploy to a staging server with a real domain and test against production with a KES 1 payment. Production C2B callbacks are significantly more reliable.

> **Production note:** In production, the URLs you register here must also be pre-approved in the Daraja portal. Attempting to register an unrecognised domain will fail silently or be rejected. Ensure your domain is listed in your approved application before calling this endpoint.

```python
def register_c2b_urls(auth_client, validation_url: str, confirmation_url: str):
    """
    Register C2B Validation and Confirmation URLs with Safaricom.

    Validation URL:    Called BEFORE transaction is processed.
                       You can accept or reject the payment here.
    Confirmation URL:  Called AFTER transaction is completed.
                       For recording successful payments.

    ResponseType options:
      "Completed" — confirms payment even if your validation URL is
                    unreachable or returns an error. The money moves
                    regardless of your validation response. Choose this
                    if uptime of your validation endpoint isn't guaranteed.
      "Cancelled" — reverses the payment if your validation URL fails.
                    Choose this only if you need strict validation and
                    your validation endpoint is highly available.
    """
    access_token = auth_client.get_access_token()
    shortcode    = os.environ.get("MPESA_SHORTCODE")
    base_url     = "https://sandbox.safaricom.co.ke"  # or production URL

    payload = {
        "ShortCode":       shortcode,
        "ResponseType":    "Completed",
        "ConfirmationURL": confirmation_url,
        "ValidationURL":   validation_url,
    }

    response = requests.post(
        f"{base_url}/mpesa/c2b/v1/registerurl",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    return response.json()
```

### Step 2: Validation URL Handler

```python
@app.route("/c2b/validate", methods=["POST"])
def c2b_validate():
    """
    C2B Validation Endpoint — called by Daraja BEFORE processing a payment.

    Return codes:
      0: Accept the transaction
      1: Reject the transaction (payment will not proceed)

    IMPORTANT: If ResponseType is "Completed" (recommended default), Safaricom
    will confirm the payment even if this endpoint is unreachable or returns
    an error. Your rejection only takes effect when the endpoint responds
    successfully with ResultCode 1.
    """
    payload = request.get_json(force=True)

    account_number = payload.get("BillRefNumber", "").strip()
    amount         = float(payload.get("TransAmount", 0))

    logger.info(f"C2B Validation: account={account_number}, amount={amount}")

    account = Account.query.filter_by(reference=account_number, active=True).first()

    if not account:
        logger.warning(f"C2B Validation rejected: unknown account {account_number}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid account number"}), 200

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

### Step 3: Confirmation URL Handler

```python
@app.route("/c2b/confirm", methods=["POST"])
def c2b_confirm():
    """
    C2B Confirmation Endpoint — called AFTER a payment completes successfully.

    IMPORTANT: The money has already moved by the time this is called.
    This endpoint is for recording purposes only. Always return 0.
    """
    try:
        payload = request.get_json(force=True)

        trans_id   = payload.get("TransID")
        account_ref = payload.get("BillRefNumber", "").strip()
        amount     = float(payload.get("TransAmount", 0))
        phone      = payload.get("MSISDN")
        trans_time = payload.get("TransTime")

        # Idempotency: check if we've already recorded this receipt
        existing = Payment.query.filter_by(mpesa_receipt=trans_id).first()
        if existing:
            logger.info(f"Duplicate confirmation for {trans_id} — ignoring")
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        payment = Payment(
            mpesa_receipt    = trans_id,
            account_reference = account_ref,
            amount           = amount,
            phone            = phone,
            transaction_time = trans_time,
            created_at       = datetime.utcnow(),
        )
        db.session.add(payment)

        invoice = Invoice.query.filter_by(reference=account_ref).first()
        if invoice:
            invoice.status       = "paid"
            invoice.paid_amount  = amount
            invoice.paid_at      = datetime.utcnow()
            invoice.mpesa_receipt = trans_id

        db.session.commit()
        logger.info(f"Payment recorded: {trans_id} for {account_ref}")

    except Exception as e:
        logger.error(f"C2B confirmation error: {e}", exc_info=True)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

### C2B Database Schema

```sql
CREATE TABLE c2b_payments (
    id               SERIAL PRIMARY KEY,
    mpesa_receipt    VARCHAR(50) UNIQUE NOT NULL,
    account_ref      VARCHAR(100) NOT NULL,
    amount           DECIMAL(12,2) NOT NULL,
    phone            VARCHAR(20),
    first_name       VARCHAR(100),
    last_name        VARCHAR(100),
    transaction_time VARCHAR(20),
    shortcode        VARCHAR(20),
    recorded_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    processed        BOOLEAN DEFAULT FALSE,
    processed_at     TIMESTAMP
);

CREATE INDEX idx_c2b_account_ref   ON c2b_payments(account_ref);
CREATE INDEX idx_c2b_mpesa_receipt ON c2b_payments(mpesa_receipt);
CREATE INDEX idx_c2b_recorded_at   ON c2b_payments(recorded_at);
```

---

## 8. B2C Integration {#8-b2c}

Business-to-Customer (B2C) lets your business send money directly to a customer's M-Pesa. Use cases include salary disbursements, refunds, withdrawal requests, and prize payments.

> **Correction note:** All B2C recipients must have a registered M-Pesa account. The `BusinessPayment` command ID refers to a general payment type — it does not enable payment to unregistered M-Pesa users. If a recipient is not registered, the transaction will fail with an appropriate error code.

### Security Credentials

B2C uses a different authentication mechanism — Security Credentials. You encrypt the Initiator Password using Safaricom's public certificate.

> **Initiator password expiry:** The web operator (initiator) password assigned to your business has an expiry period — typically around 3 months. If your B2C requests start failing with authentication errors after previously working, your initiator password may have expired. Log in to the M-Pesa business portal to reset it. When it expires, the web operator account becomes dormant and must be reactivated by the Business Administrator.

> **Important about certificates:** Safaricom provides separate certificate files for sandbox and production. Both must be downloaded from the Daraja portal. The sandbox certificate expires periodically — if your B2C requests suddenly start failing with credential errors, download a fresh sandbox certificate from the portal. Never fetch or generate these certificates programmatically; they are issued by Safaricom and must be stored as files in your application.

```python
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

def generate_security_credential(initiator_password: str, environment: str = "sandbox") -> str:
    """
    Encrypt the initiator password with Safaricom's public certificate.

    Certificates must be downloaded manually from the Daraja portal:
      Sandbox:    developer.safaricom.co.ke → APIs → Certificates → Sandbox
      Production: developer.safaricom.co.ke → APIs → Certificates → Production

    The sandbox certificate expires periodically. If B2C calls suddenly fail
    with credential errors, download a fresh certificate from the portal.
    """
    cert_path = (
        "certs/sandbox_cert.cer"
        if environment == "sandbox"
        else "certs/production_cert.cer"
    )

    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()

    certificate = load_pem_x509_certificate(cert_data)
    public_key  = certificate.public_key()

    # Safaricom requires RSA with PKCS#1 v1.5 padding
    encrypted = public_key.encrypt(
        initiator_password.encode("utf-8"),
        padding.PKCS1v15()
    )

    return base64.b64encode(encrypted).decode("utf-8")
```

### B2C Payment Request

```python
class B2CPayment:
    """Handles Business-to-Customer payments via Daraja B2C API."""

    def __init__(self, auth_client):
        self.auth             = auth_client
        self.environment      = os.environ.get("MPESA_ENV", "sandbox")
        self.shortcode        = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name   = os.environ.get("MPESA_INITIATOR_NAME")
        self.initiator_password = os.environ.get("MPESA_INITIATOR_PASSWORD")
        self.result_url       = os.environ.get("MPESA_B2C_RESULT_URL")
        self.timeout_url      = os.environ.get("MPESA_B2C_TIMEOUT_URL")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        self._security_credential = generate_security_credential(
            self.initiator_password, self.environment
        )

    def send_payment(
        self,
        phone_number: str,
        amount: int,
        remarks: str,
        occasion: str = "",
        command_id: str = "BusinessPayment"
    ) -> dict:
        """
        Send money from your business account to a customer.

        command_id options:
          "BusinessPayment":  Standard B2C payment
          "SalaryPayment":    For salary disbursement
          "PromotionPayment": For promotions/incentives (lower limits apply)

        All recipients must have a registered M-Pesa account.
        """
        normalized_phone = self._normalize_phone(phone_number)
        access_token     = self.auth.get_access_token()

        payload = {
            "InitiatorName":      self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID":          command_id,
            "Amount":             amount,
            "PartyA":             self.shortcode,
            "PartyB":             normalized_phone,
            "Remarks":            remarks,
            "QueueTimeOutURL":    self.timeout_url,
            "ResultURL":          self.result_url,
            "Occasion":           occasion,
        }

        response = requests.post(
            f"{self.base_url}/mpesa/b2c/v1/paymentrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )

        data = response.json()

        if data.get("ResponseCode") == "0":
            return {
                "success":                    True,
                "conversation_id":            data.get("ConversationID"),
                "originator_conversation_id": data.get("OriginatorConversationID"),
                "response_description":       data.get("ResponseDescription"),
            }

        return {"success": False, "error": data.get("ResponseDescription"), "raw": data}

    def _normalize_phone(self, phone: str) -> str:
        phone = phone.strip().replace(" ", "")
        if phone.startswith("+"): phone = phone[1:]
        if phone.startswith("0"): phone = "254" + phone[1:]
        return phone
```

### B2C Result Callback

```python
@app.route("/b2c/result", methods=["POST"])
def b2c_result():
    try:
        payload  = request.get_json(force=True)
        result   = payload.get("Result", {})
        result_code   = result.get("ResultCode")
        originator_id = result.get("OriginatorConversationID")
        result_desc   = result.get("ResultDesc")

        disbursement = Disbursement.query.filter_by(originator_id=originator_id).first()

        if result_code == 0:
            params_list = result.get("ResultParameters", {}).get("ResultParameter", [])
            params      = {p["Key"]: p.get("Value") for p in params_list}

            if disbursement:
                disbursement.status       = "completed"
                disbursement.mpesa_receipt = params.get("TransactionReceipt")
                disbursement.completed_at = datetime.utcnow()
                db.session.commit()

            logger.info(f"B2C Success: {params.get('TransactionReceipt')}")
        else:
            if disbursement:
                disbursement.status         = "failed"
                disbursement.failure_reason = result_desc
                disbursement.failed_at      = datetime.utcnow()
                db.session.commit()

            logger.warning(f"B2C Failed ({result_code}): {result_desc}")

    except Exception as e:
        logger.error(f"B2C result processing error: {e}", exc_info=True)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


@app.route("/b2c/timeout", methods=["POST"])
def b2c_timeout():
    """
    Called when a B2C request times out at Safaricom's queue.
    This does NOT mean the transaction failed definitively —
    it means the queue timed out. Always verify with Transaction Status API.
    """
    payload = request.get_json(force=True)
    logger.warning(f"B2C Timeout — verify with Transaction Status API: {payload}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

---

## 9. Transaction Status API {#9-transaction-status}

### Why Transaction Verification Matters

In production, things go wrong: your server crashes after initiating a payment but before receiving the callback; network issues cause callbacks to be lost; Daraja's callback service has an outage. Without Transaction Status, you'd have payments in an unknown state.

```python
class TransactionStatus:
    """Query the status of any M-Pesa transaction."""

    def __init__(self, auth_client):
        self.auth             = auth_client
        self.environment      = os.environ.get("MPESA_ENV", "sandbox")
        self.shortcode        = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name   = os.environ.get("MPESA_INITIATOR_NAME")
        self.initiator_password = os.environ.get("MPESA_INITIATOR_PASSWORD")
        self.result_url       = os.environ.get("MPESA_STATUS_RESULT_URL")
        self.timeout_url      = os.environ.get("MPESA_STATUS_TIMEOUT_URL")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        self._security_credential = generate_security_credential(
            self.initiator_password, self.environment
        )

    def check(self, transaction_id: str, identifier_type: int = 4) -> dict:
        """
        Query the status of a transaction.

        identifier_type: 4 = Organization shortcode (most common)
        The result arrives asynchronously to your result_url.
        """
        access_token = self.auth.get_access_token()

        payload = {
            "Initiator":          self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID":          "TransactionStatusQuery",
            "TransactionID":      transaction_id,
            "PartyA":             self.shortcode,
            "IdentifierType":     str(identifier_type),
            "ResultURL":          self.result_url,
            "QueueTimeOutURL":    self.timeout_url,
            "Remarks":            "Transaction status check",
            "Occasion":           "",
        }

        response = requests.post(
            f"{self.base_url}/mpesa/transactionstatus/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        return response.json()


@app.route("/transaction-status/result", methods=["POST"])
def transaction_status_result():
    payload     = request.get_json(force=True)
    result      = payload.get("Result", {})
    result_code = result.get("ResultCode")
    transaction_id = result.get("TransactionID")

    if result_code == 0:
        params_list        = result.get("ResultParameters", {}).get("ResultParameter", [])
        params             = {p["Key"]: p.get("Value") for p in params_list}
        transaction_status = params.get("TransactionStatus")
        amount             = params.get("Amount")

        reconcile_transaction(transaction_id, transaction_status, amount, params)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200


def reconcile_transaction(transaction_id: str, status: str, amount, metadata: dict):
    transaction = Transaction.query.filter_by(mpesa_receipt=transaction_id).first()

    if transaction and status == "Completed" and transaction.status == "pending":
        transaction.status           = "completed"
        transaction.amount_confirmed = amount
        transaction.reconciled_at    = datetime.utcnow()
        transaction.reconcile_method = "status_query"
        db.session.commit()

        if transaction.order_id:
            fulfill_order(transaction.order_id)

        logger.info(f"Reconciled transaction {transaction_id}")
```

### Reconciliation Workflow

```python
import schedule
import time

def run_reconciliation():
    """
    Periodic reconciliation job.
    Run every 30–60 minutes to catch missed callbacks.
    """
    fifteen_min_ago = datetime.utcnow() - timedelta(minutes=15)

    pending_transactions = Transaction.query.filter(
        Transaction.status == "pending",
        Transaction.created_at < fifteen_min_ago
    ).all()

    logger.info(f"Reconciliation: {len(pending_transactions)} pending transactions")

    for transaction in pending_transactions:
        if transaction.checkout_request_id:
            result      = stk_push.query_status(transaction.checkout_request_id)
            result_code = result.get("ResultCode")

            if result_code == "0":
                transaction.status = "completed"
            elif result_code in ["1032", "1037", "2001"]:
                transaction.status         = "failed"
                transaction.failure_reason = result.get("ResultDesc")
            # "500.001.1001" means still processing — leave pending

        time.sleep(0.5)  # Be gentle on the API

    db.session.commit()

schedule.every(30).minutes.do(run_reconciliation)
```

---

## 10. Account Balance API {#10-account-balance}

```python
class AccountBalance:
    """Query your M-Pesa business account balance."""

    def __init__(self, auth_client):
        self.auth             = auth_client
        self.environment      = os.environ.get("MPESA_ENV", "sandbox")
        self.shortcode        = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name   = os.environ.get("MPESA_INITIATOR_NAME")
        self.initiator_password = os.environ.get("MPESA_INITIATOR_PASSWORD")
        self.result_url       = os.environ.get("MPESA_BALANCE_RESULT_URL")
        self.timeout_url      = os.environ.get("MPESA_BALANCE_TIMEOUT_URL")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        self._security_credential = generate_security_credential(
            self.initiator_password, self.environment
        )

    def query(self, identifier_type: int = 4) -> dict:
        """Request an account balance query. Result arrives via result_url."""
        access_token = self.auth.get_access_token()

        payload = {
            "Initiator":          self.initiator_name,
            "SecurityCredential": self._security_credential,
            "CommandID":          "AccountBalance",
            "PartyA":             self.shortcode,
            "IdentifierType":     str(identifier_type),
            "Remarks":            "Balance inquiry",
            "QueueTimeOutURL":    self.timeout_url,
            "ResultURL":          self.result_url,
        }

        response = requests.post(
            f"{self.base_url}/mpesa/accountbalance/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        return response.json()


@app.route("/balance/result", methods=["POST"])
def balance_result():
    payload = request.get_json(force=True)
    result  = payload.get("Result", {})

    if result.get("ResultCode") == 0:
        params_list = result.get("ResultParameters", {}).get("ResultParameter", [])
        params      = {p["Key"]: p.get("Value") for p in params_list}

        # Format: "Working Account|KES|232572.00|232572.00|0.00|0.00"
        # Parts:   AccountType|Currency|CurrentBalance|AvailableBalance|Reserved|UnCleared
        balance_string = params.get("AccountBalance", "")

        balances = {}
        for account_str in balance_string.split("&"):
            parts = account_str.split("|")
            if len(parts) >= 4:
                balances[parts[0]] = {
                    "currency":          parts[1],
                    "current_balance":   float(parts[2]),
                    "available_balance": float(parts[3]),
                }

        logger.info(f"Balance query result: {balances}")
        cache_balance(balances)

        working_balance   = balances.get("Working Account", {}).get("available_balance", 0)
        LOW_BALANCE_THRESHOLD = float(os.environ.get("LOW_BALANCE_THRESHOLD", "10000"))

        if working_balance < LOW_BALANCE_THRESHOLD:
            send_low_balance_alert(working_balance)

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

---

## 11. Reversal API {#11-reversals}

### When to Use Reversals

Reversals allow you to reverse a completed M-Pesa transaction within **24 hours** of completion.

> **Important limitations:** Reversals are not instant — they take time and can be rejected by Safaricom. Some transaction types cannot be reversed. The customer receives the reversed amount back into their M-Pesa. For amounts above certain thresholds, Safaricom may require additional verification.

```python
class TransactionReversal:
    """Reverse a completed M-Pesa transaction."""

    def __init__(self, auth_client):
        self.auth             = auth_client
        self.environment      = os.environ.get("MPESA_ENV", "sandbox")
        self.shortcode        = os.environ.get("MPESA_SHORTCODE")
        self.initiator_name   = os.environ.get("MPESA_INITIATOR_NAME")
        self.initiator_password = os.environ.get("MPESA_INITIATOR_PASSWORD")
        self.result_url       = os.environ.get("MPESA_REVERSAL_RESULT_URL")
        self.timeout_url      = os.environ.get("MPESA_REVERSAL_TIMEOUT_URL")

        self.base_url = (
            "https://api.safaricom.co.ke"
            if self.environment == "production"
            else "https://sandbox.safaricom.co.ke"
        )

        self._security_credential = generate_security_credential(
            self.initiator_password, self.environment
        )

    def reverse(
        self,
        transaction_id: str,
        amount: int,
        receiver_party: str,
        remarks: str = "Reversal",
        receiver_identifier_type: int = 1,
    ) -> dict:
        """
        Initiate a transaction reversal.

        Args:
            transaction_id: M-Pesa receipt number to reverse
            amount: Amount to reverse (must match original)
            receiver_party: Customer phone number
            remarks: Reason for reversal (audit trail)
            receiver_identifier_type: 1 = MSISDN (phone number)
        """
        access_token = self.auth.get_access_token()

        payload = {
            "Initiator":              self.initiator_name,
            "SecurityCredential":     self._security_credential,
            "CommandID":              "TransactionReversal",
            "TransactionID":          transaction_id,
            "Amount":                 amount,
            "ReceiverParty":          receiver_party,
            "RecieverIdentifierType": str(receiver_identifier_type),
            "Remarks":                remarks,
            "QueueTimeOutURL":        self.timeout_url,
            "ResultURL":              self.result_url,
            "Occasion":               "",
        }

        response = requests.post(
            f"{self.base_url}/mpesa/reversal/v1/request",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        data = response.json()

        return {
            "accepted":             data.get("ResponseCode") == "0",
            "conversation_id":      data.get("ConversationID"),
            "response_description": data.get("ResponseDescription"),
            "raw":                  data,
        }

    def process_refund_request(self, original_transaction_id: str, reason: str) -> dict:
        """Business-logic wrapper for customer refund requests."""
        original = Transaction.query.filter_by(
            mpesa_receipt=original_transaction_id,
            status="completed"
        ).first()

        if not original:
            return {"success": False, "error": "Transaction not found or not completed"}

        if datetime.utcnow() - original.completed_at > timedelta(hours=24):
            return {"success": False, "error": "Transaction is more than 24 hours old"}

        if original.reversed:
            return {"success": False, "error": "Transaction already reversed"}

        result = self.reverse(
            transaction_id=original_transaction_id,
            amount=int(original.amount),
            receiver_party=original.phone,
            remarks=reason,
        )

        if result["accepted"]:
            original.reversal_status       = "pending"
            original.reversal_requested_at = datetime.utcnow()
            original.reversal_reason       = reason
            db.session.commit()

        return result


@app.route("/reversal/result", methods=["POST"])
def reversal_result():
    payload        = request.get_json(force=True)
    result         = payload.get("Result", {})
    result_code    = result.get("ResultCode")
    transaction_id = result.get("TransactionID")

    transaction = Transaction.query.filter_by(mpesa_receipt=transaction_id).first()

    if transaction:
        if result_code == 0:
            transaction.reversed              = True
            transaction.reversal_status       = "completed"
            transaction.reversal_completed_at = datetime.utcnow()
        else:
            transaction.reversal_status         = "failed"
            transaction.reversal_failure_reason = result.get("ResultDesc")

        db.session.commit()

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

---

## 12. Database Design {#12-database}

### Complete Schema

```sql
-- ═══════════════════════════════════════════════════════════════
-- USERS
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    phone      VARCHAR(20) UNIQUE NOT NULL,  -- Normalized: 254XXXXXXXXX
    email      VARCHAR(255) UNIQUE,
    name       VARCHAR(255),
    mpesa_name VARCHAR(255),                 -- Name from M-Pesa callbacks
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_phone ON users(phone);

-- ═══════════════════════════════════════════════════════════════
-- ORDERS
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE orders (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER REFERENCES users(id),
    reference VARCHAR(50) UNIQUE NOT NULL,
    amount    DECIMAL(12,2) NOT NULL,
    currency  VARCHAR(3) NOT NULL DEFAULT 'KES',
    status    VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | paid | failed | cancelled | refunded
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    paid_at    TIMESTAMP
);
CREATE INDEX idx_orders_user_id   ON orders(user_id);
CREATE INDEX idx_orders_reference ON orders(reference);
CREATE INDEX idx_orders_status    ON orders(status);

-- ═══════════════════════════════════════════════════════════════
-- TRANSACTIONS — core table for all M-Pesa transaction attempts
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE transactions (
    id                    SERIAL PRIMARY KEY,
    order_id              INTEGER REFERENCES orders(id),
    user_id               INTEGER REFERENCES users(id),
    transaction_type      VARCHAR(30) NOT NULL,  -- stk_push | c2b | b2c | reversal
    checkout_request_id   VARCHAR(100) UNIQUE,
    merchant_request_id   VARCHAR(100),
    conversation_id       VARCHAR(100),
    originator_conv_id    VARCHAR(100),
    mpesa_receipt         VARCHAR(50) UNIQUE,
    amount_requested      DECIMAL(12,2) NOT NULL,
    amount_confirmed      DECIMAL(12,2),
    currency              VARCHAR(3) DEFAULT 'KES',
    phone_number          VARCHAR(20),
    status                VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | completed | failed | cancelled | timed_out | reversed
    result_code           VARCHAR(20),
    result_desc           TEXT,
    failure_reason        TEXT,
    reversed              BOOLEAN DEFAULT FALSE,
    reversal_status       VARCHAR(20),
    reversal_reason       TEXT,
    reversal_requested_at TIMESTAMP,
    reversal_completed_at TIMESTAMP,
    reconciled            BOOLEAN DEFAULT FALSE,
    reconcile_method      VARCHAR(30),  -- callback | status_query | manual
    created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at          TIMESTAMP,
    failed_at             TIMESTAMP
);
CREATE INDEX idx_txn_checkout_id  ON transactions(checkout_request_id);
CREATE INDEX idx_txn_mpesa_receipt ON transactions(mpesa_receipt);
CREATE INDEX idx_txn_status       ON transactions(status);
CREATE INDEX idx_txn_phone        ON transactions(phone_number);
CREATE INDEX idx_txn_created_at   ON transactions(created_at);
CREATE INDEX idx_txn_order_id     ON transactions(order_id);

-- ═══════════════════════════════════════════════════════════════
-- CALLBACK LOGS — raw log of every Daraja callback received
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE callback_logs (
    id                SERIAL PRIMARY KEY,
    transaction_id    INTEGER REFERENCES transactions(id),
    callback_type     VARCHAR(30) NOT NULL,
    raw_payload       JSONB NOT NULL,
    processing_status VARCHAR(20) DEFAULT 'received',
    ip_address        VARCHAR(45),
    received_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at      TIMESTAMP
);
CREATE INDEX idx_callback_txn_id      ON callback_logs(transaction_id);
CREATE INDEX idx_callback_type        ON callback_logs(callback_type);
CREATE INDEX idx_callback_received_at ON callback_logs(received_at);

-- ═══════════════════════════════════════════════════════════════
-- AUDIT TRAILS — immutable log of all state changes
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE audit_trails (
    id           SERIAL PRIMARY KEY,
    entity_type  VARCHAR(30) NOT NULL,
    entity_id    INTEGER NOT NULL,
    action       VARCHAR(50) NOT NULL,
    old_value    JSONB,
    new_value    JSONB,
    performed_by VARCHAR(100),
    performed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address   VARCHAR(45),
    notes        TEXT
);
CREATE INDEX idx_audit_entity       ON audit_trails(entity_type, entity_id);
CREATE INDEX idx_audit_performed_at ON audit_trails(performed_at);

-- ═══════════════════════════════════════════════════════════════
-- DISBURSEMENTS — B2C payment records
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE disbursements (
    id               SERIAL PRIMARY KEY,
    recipient_phone  VARCHAR(20) NOT NULL,
    recipient_name   VARCHAR(255),
    amount           DECIMAL(12,2) NOT NULL,
    purpose          VARCHAR(100),
    originator_id    VARCHAR(100) UNIQUE,
    mpesa_receipt    VARCHAR(50),
    status           VARCHAR(20) DEFAULT 'pending',
    failure_reason   TEXT,
    requested_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMP
);
CREATE INDEX idx_disbursement_phone  ON disbursements(recipient_phone);
CREATE INDEX idx_disbursement_status ON disbursements(status);
```

### SQLAlchemy Models (Python)

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id                  = Column(Integer, primary_key=True)
    order_id            = Column(Integer)
    user_id             = Column(Integer)
    transaction_type    = Column(String(30), nullable=False)
    checkout_request_id = Column(String(100), unique=True)
    merchant_request_id = Column(String(100))
    mpesa_receipt       = Column(String(50), unique=True)
    amount_requested    = Column(Numeric(12, 2), nullable=False)
    amount_confirmed    = Column(Numeric(12, 2))
    phone_number        = Column(String(20))
    status              = Column(String(20), nullable=False, default="pending")
    result_code         = Column(String(20))
    result_desc         = Column(Text)
    failure_reason      = Column(Text)
    reversed            = Column(Boolean, default=False)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at        = Column(DateTime)
    failed_at           = Column(DateTime)

    def to_dict(self):
        return {
            "id":           self.id,
            "status":       self.status,
            "amount":       float(self.amount_requested),
            "mpesa_receipt": self.mpesa_receipt,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }


class CallbackLog(Base):
    __tablename__ = "callback_logs"

    id                = Column(Integer, primary_key=True)
    transaction_id    = Column(Integer)
    callback_type     = Column(String(30), nullable=False)
    raw_payload       = Column(JSON, nullable=False)
    processing_status = Column(String(20), default="received")
    ip_address        = Column(String(45))
    received_at       = Column(DateTime, default=datetime.utcnow)
    processed_at      = Column(DateTime)
```

---

## 13. Security Best Practices {#13-security}

### Environment Variables and Secret Management

Never hardcode credentials. Use environment variables, and in production, a secrets manager:

```bash
# Development: .env file — NEVER commit to git
MPESA_CONSUMER_KEY=your_key_here
MPESA_CONSUMER_SECRET=your_secret_here
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_passkey_here
MPESA_INITIATOR_NAME=testapi
MPESA_INITIATOR_PASSWORD=your_initiator_password
MPESA_CALLBACK_URL=https://yourdomain.com/callbacks/mpesa/stk
MPESA_ENV=sandbox
```

```python
# Production: load from AWS Secrets Manager
import boto3, json, os

def load_mpesa_secrets():
    client = boto3.client("secretsmanager", region_name="af-south-1")
    try:
        response = client.get_secret_value(SecretId="prod/mpesa/daraja")
        secrets  = json.loads(response["SecretString"])
        os.environ.update({
            "MPESA_CONSUMER_KEY":    secrets["consumer_key"],
            "MPESA_CONSUMER_SECRET": secrets["consumer_secret"],
            "MPESA_SHORTCODE":       secrets["shortcode"],
            "MPESA_PASSKEY":         secrets["passkey"],
        })
    except Exception as e:
        raise RuntimeError(f"Failed to load M-Pesa secrets: {e}")
```

### Callback Validation

Safaricom doesn't sign callbacks with HMAC (unlike Stripe or GitHub). The available validation approach is IP allowlisting.

> **Important disclaimer:** The IP ranges below are commonly documented but Safaricom does not publish a versioned, authoritative IP list with update notifications. IP ranges can change without notice. Always verify the current list against the official Safaricom Daraja documentation at [developer.safaricom.co.ke](https://developer.safaricom.co.ke) before deploying. Treat IP validation as one layer of defence — not as a standalone security guarantee. Combine it with payload schema validation.

```python
# Verify current ranges at developer.safaricom.co.ke before deploying
SAFARICOM_IPS = {
    "sandbox": [
        "196.201.214.200", "196.201.214.206", "196.201.213.114",
        "196.201.214.207", "196.201.214.208", "196.201.213.44",
        "196.201.212.127", "196.201.212.128", "196.201.212.129",
        "196.201.212.136", "196.201.212.138",
    ],
    "production": [
        "196.201.214.200", "196.201.214.206", "196.201.213.114",
        "196.201.214.207", "196.201.214.208", "196.201.213.44",
        "196.201.212.127", "196.201.212.128", "196.201.212.129",
        "196.201.212.136", "196.201.212.138",
    ],
}

def validate_safaricom_ip(request) -> bool:
    """
    Validate that a callback comes from a known Safaricom IP.

    IMPORTANT: This is a secondary security layer, not a primary one.
    IP ranges may change. Always verify the list against current
    Safaricom documentation.
    """
    environment = os.environ.get("MPESA_ENV", "sandbox")
    allowed_ips = SAFARICOM_IPS.get(environment, [])

    # X-Forwarded-For: client, proxy1, proxy2 — use first value
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip     = forwarded_for.split(",")[0].strip() if forwarded_for else request.remote_addr

    if client_ip not in allowed_ips:
        logger.warning(f"Callback from unrecognised IP: {client_ip}")
        return False
    return True


def validate_callback_payload(payload: dict) -> bool:
    """
    Validate callback payload schema — a second layer beyond IP checking.
    Rejects structurally invalid payloads regardless of source IP.
    """
    try:
        callback = payload.get("Body", {}).get("stkCallback", {})
        required_fields = ["MerchantRequestID", "CheckoutRequestID", "ResultCode"]
        return all(field in callback for field in required_fields)
    except Exception:
        return False


@app.route("/callbacks/mpesa/stk", methods=["POST"])
def stk_callback():
    if not validate_safaricom_ip(request):
        logger.error(f"Unauthorized callback IP: {request.remote_addr}")
        # Return 200 silently — don't tip off a potential attacker
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    payload = request.get_json(force=True) or {}

    if not validate_callback_payload(payload):
        logger.warning(f"Malformed callback payload from {request.remote_addr}")
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    # ... rest of processing
```

### Preventing Duplicate Transactions

```python
import hashlib
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=1)

def is_duplicate_request(phone: str, amount: int, order_id: str) -> bool:
    """
    Prevent the same payment from being initiated twice within 60 seconds.
    Uses SHA-256 (not MD5) for the fingerprint to pass security audits.
    """
    fingerprint = f"{phone}:{amount}:{order_id}"
    key         = f"payment_lock:{hashlib.sha256(fingerprint.encode()).hexdigest()}"

    # SET key "locked" NX EX 60 — only sets if not already present
    was_set = redis_client.set(key, "locked", nx=True, ex=60)
    return not was_set  # True if duplicate (key already existed)
```

### Preventing Replay Attacks

```python
from datetime import timezone

def validate_callback_timestamp(payload: dict, tolerance_seconds: int = 300) -> bool:
    """
    Validate that a callback isn't a replayed old request.

    IMPORTANT: The TransactionDate in STK Push callbacks is in Kenya time
    (EAT, UTC+3). This function converts it to UTC before comparing.
    Failing to account for the timezone offset causes legitimate callbacks
    near the tolerance window to be incorrectly rejected.
    """
    try:
        items = (
            payload.get("Body", {})
            .get("stkCallback", {})
            .get("CallbackMetadata", {})
            .get("Item", [])
        )
        meta = {item["Name"]: item.get("Value") for item in items}
        transaction_date_str = str(meta.get("TransactionDate", ""))

        if transaction_date_str:
            # Format: 20191219102115 = YYYYMMDDHHmmss in EAT (UTC+3)
            from datetime import timedelta
            txn_time_eat = datetime.strptime(transaction_date_str, "%Y%m%d%H%M%S")
            # Convert EAT to UTC by subtracting 3 hours
            txn_time_utc = txn_time_eat - timedelta(hours=3)
            age          = datetime.utcnow() - txn_time_utc

            if age.total_seconds() > tolerance_seconds:
                logger.warning(f"Possible replay: callback is {age.total_seconds():.0f}s old")
                return False

    except Exception:
        # If we cannot validate, allow through but log
        logger.warning("Could not validate callback timestamp — allowing through")

    return True
```

### Rate Limiting Callbacks

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address, default_limits=["200 per minute"])

@app.route("/callbacks/mpesa/stk", methods=["POST"])
@limiter.limit("30 per minute")
def stk_callback():
    pass  # handler code
```

### Structured Logging

```python
import logging, json
from datetime import datetime

class PaymentLogger:
    def __init__(self):
        self.logger = logging.getLogger("payments")

    def log_initiation(self, phone: str, amount: int, checkout_id: str, order_id: str):
        self.logger.info(json.dumps({
            "event":               "payment_initiated",
            "phone":               phone[:6] + "****",  # mask for privacy
            "amount":              amount,
            "checkout_request_id": checkout_id,
            "order_id":            order_id,
            "timestamp":           datetime.utcnow().isoformat(),
        }))

    def log_callback(self, checkout_id: str, result_code: int, mpesa_receipt: str = None):
        self.logger.info(json.dumps({
            "event":               "payment_callback",
            "checkout_request_id": checkout_id,
            "result_code":         result_code,
            "success":             result_code == 0,
            "mpesa_receipt":       mpesa_receipt,
            "timestamp":           datetime.utcnow().isoformat(),
        }))

    def log_security_event(self, event_type: str, details: dict, ip: str):
        self.logger.warning(json.dumps({
            "event":      f"security_{event_type}",
            "ip_address": ip,
            "details":    details,
            "timestamp":  datetime.utcnow().isoformat(),
        }))

payment_logger = PaymentLogger()
```

---

## 14. Production Deployment {#14-production}

### Moving from Sandbox to Production

**Step 1: Complete development and testing**
- All callback URLs must be HTTPS with valid SSL certificates
- Callbacks must respond within 10 seconds
- All error scenarios handled gracefully
- Proper logging and monitoring implemented

**Step 2: Register and pre-approve callback URLs in the Daraja portal**

> **Critical — production callback URL registration:** Unlike sandbox, production Daraja **will not deliver callbacks to arbitrary URLs**. You must pre-register all callback URLs (STK, C2B, B2C, etc.) through the Daraja portal under your approved application before going live. Passing an unregistered URL in the `CallBackURL` field will result in callbacks being silently dropped. Register URLs via: *My Apps → [Your App] → Go Live → Callback URLs*.

**Step 3: Apply for Go-Live**

In the Daraja portal:
1. Go to your app → "Go Live"
2. Submit your application with:
   - Business registration certificate
   - KRA PIN certificate
   - Director/Authorized person ID
   - Application description and business justification
   - Screenshots of your application
   - Test evidence (screenshots of sandbox tests)

**Step 4: Safaricom Review (3–10 business days)**

Safaricom reviews:
- Business legitimacy
- Application purpose
- Technical readiness
- Compliance with their terms of service

> **Timeline reality check:** From first sandbox success to a production-ready launch, six to eight weeks is a typical timeline for a well-prepared team — longer if you discover the C2B/B2C shortcode constraint late, or if your go-live documents are incomplete. Safaricom will also whitelist your production server IPs as part of the approval process; have your server IP addresses ready.

> **After approval:** B2C and B2B are **not automatically enabled** even once your app goes live. Contact Safaricom API support (`apisupport@safaricom.co.ke` or call 2222 from a Safaricom line) to request explicit whitelisting of these APIs on your shortcode. STK Push and C2B are usually activated automatically.

**Step 5: Update Configuration**

> **If migrating from the old SOAP/G2 API:** If your shortcode was previously registered with Safaricom's legacy SOAP API, you must request Safaricom's support team to delete the old registered C2B URLs from the legacy system **before** your new Daraja integration will work correctly. Old registered URLs in the SOAP system conflict with Daraja registrations. Email `apisupport@safaricom.co.ke` with your shortcode and request cleanup of legacy URL registrations.

```python
# config.py
import os

class Config:
    MPESA_ENV = os.environ.get("MPESA_ENV", "sandbox")

    @property
    def mpesa_base_url(self):
        if self.MPESA_ENV == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    # Production shortcodes differ from sandbox test shortcodes
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE")
    MPESA_PASSKEY   = os.environ.get("MPESA_PASSKEY")
```

### SSL Requirements

- Callback URLs **must** use HTTPS
- Self-signed certificates will not work
- Use Let's Encrypt for free trusted certificates

```bash
sudo apt update && sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Verify auto-renewal
sudo systemctl status certbot.timer
```

### Nginx Configuration for Callbacks

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains";

    location /callbacks/mpesa/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout    30s;
        proxy_connect_timeout 10s;
    }

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Monitoring and Alerting

```python
from prometheus_client import Counter, Histogram, Gauge

payment_attempts = Counter(
    'mpesa_payment_attempts_total',
    'Total payment initiation attempts',
    ['type', 'status']
)

payment_callbacks = Counter(
    'mpesa_callbacks_total',
    'Total callbacks received',
    ['type', 'result']
)

callback_processing_time = Histogram(
    'mpesa_callback_processing_seconds',
    'Time to process a callback',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

pending_transactions = Gauge(
    'mpesa_pending_transactions',
    'Number of transactions awaiting callback'
)


def send_alert(title: str, message: str, severity: str = "warning"):
    import slack_sdk
    client = slack_sdk.WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    emoji  = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")
    client.chat_postMessage(
        channel="#payments-alerts",
        text=f"{emoji} *{title}*\n{message}"
    )

# Alert when:
# - Callback success rate drops below 95%
# - More than 20 pending transactions older than 15 minutes
# - Authentication failures
# - Unusual volume spike (possible fraud)
# - Low M-Pesa account balance (for B2C)
```

---

## 15. Building a Complete Real-World Project {#15-project}

### E-Commerce Checkout with M-Pesa

A complete payment flow: product browsing → cart → checkout → M-Pesa payment → order confirmation, incorporating the queue-based and idempotency patterns from Section 16.

### Project Structure

```
shop/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── mpesa/
│   │   ├── auth.py
│   │   ├── stk_push.py
│   │   ├── callbacks.py
│   │   └── utils.py
│   ├── api/
│   │   ├── orders.py
│   │   ├── payments.py
│   │   └── webhooks.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── checkout.html
│   ├── payment_status.html
│   └── js/
│       ├── checkout.js
│       └── payment.js
└── docker-compose.yml
```

### Backend: Payment Initiation Endpoint

```python
# api/payments.py
from flask import Blueprint, request, jsonify
from models import Order, Transaction, db
from mpesa.stk_push import STKPush
from mpesa.auth import DarajaAuth
import logging

payment_bp = Blueprint("payments", __name__)
logger     = logging.getLogger(__name__)

auth = DarajaAuth()
stk  = STKPush(auth)


@payment_bp.route("/api/orders/<order_id>/pay", methods=["POST"])
def initiate_payment(order_id):
    """Initiate M-Pesa payment for an order."""
    data  = request.get_json()
    phone = data.get("phone_number")

    if not phone:
        return jsonify({"error": "phone_number is required"}), 400

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status != "pending":
        return jsonify({"error": "Order is not in a payable state"}), 400

    if is_duplicate_request(phone, order.amount, order_id):
        existing_txn = Transaction.query.filter_by(
            order_id=order_id, status="pending"
        ).order_by(Transaction.created_at.desc()).first()

        return jsonify({
            "success":             True,
            "checkout_request_id": existing_txn.checkout_request_id if existing_txn else None,
            "message":             "Payment request already sent. Please check your phone.",
        })

    # Create transaction record BEFORE initiating — ensures the callback
    # always has a record to land on, even if it arrives before we commit.
    transaction = Transaction(
        order_id           = order.id,
        transaction_type   = "stk_push",
        amount_requested   = order.amount,
        phone_number       = phone,
        status             = "pending",
    )
    db.session.add(transaction)
    db.session.flush()  # Get the ID without committing

    try:
        result = stk.initiate(
            phone_number            = phone,
            amount                  = int(order.amount),
            account_reference       = order.reference,
            transaction_description = f"Order {order.reference}",
        )

        if result["success"]:
            transaction.checkout_request_id = result["checkout_request_id"]
            transaction.merchant_request_id = result["merchant_request_id"]
            db.session.commit()

            return jsonify({
                "success":             True,
                "checkout_request_id": result["checkout_request_id"],
                "message":             "Payment request sent. Enter your M-Pesa PIN to complete.",
            })
        else:
            transaction.status         = "failed"
            transaction.failure_reason = result.get("error")
            db.session.commit()
            return jsonify({"success": False, "error": result.get("error")}), 400

    except Exception as e:
        transaction.status         = "failed"
        transaction.failure_reason = str(e)
        db.session.commit()
        logger.error(f"Payment initiation error for order {order_id}: {e}", exc_info=True)
        return jsonify({"error": "Payment service temporarily unavailable."}), 500


@payment_bp.route("/api/payments/<checkout_id>/status", methods=["GET"])
def payment_status(checkout_id):
    """Poll endpoint — frontend calls this every 3 seconds."""
    transaction = Transaction.query.filter_by(checkout_request_id=checkout_id).first()

    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    response = {"status": transaction.status, "amount": float(transaction.amount_requested)}

    if transaction.status == "completed":
        response["mpesa_receipt"] = transaction.mpesa_receipt
        response["order_id"]      = transaction.order_id
    elif transaction.status == "failed":
        response["failure_reason"] = transaction.failure_reason

    return jsonify(response)
```

### Frontend: Checkout JavaScript

```javascript
// js/payment.js

class MpesaPayment {
  constructor() {
    this.pollingInterval     = null;
    this.maxPollingAttempts  = 30;   // 30 × 3s = 90 seconds max
    this.pollingAttempts     = 0;
  }

  async initiatePayment(orderId, phoneNumber) {
    this.showLoadingState('Sending payment request to your phone...');

    try {
      const response = await fetch(`/api/orders/${orderId}/pay`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ phone_number: phoneNumber }),
      });
      const data = await response.json();

      if (data.success) {
        this.showWaitingState(data.message);
        this.startPolling(data.checkout_request_id, orderId);
      } else {
        this.showError(data.error || 'Payment request failed. Please try again.');
      }
    } catch (error) {
      this.showError('Connection error. Please check your internet and try again.');
    }
  }

  startPolling(checkoutRequestId, orderId) {
    this.pollingAttempts = 0;

    this.pollingInterval = setInterval(async () => {
      this.pollingAttempts++;

      if (this.pollingAttempts >= this.maxPollingAttempts) {
        this.stopPolling();
        this.showTimeout('Confirmation is taking longer than expected. Check your M-Pesa messages or contact support.');
        return;
      }

      try {
        const response = await fetch(`/api/payments/${checkoutRequestId}/status`);
        const data     = await response.json();

        if (data.status === 'completed') {
          this.stopPolling();
          this.showSuccess(data.mpesa_receipt, orderId);
        } else if (data.status === 'failed') {
          this.stopPolling();
          this.showError(`Payment failed: ${data.failure_reason}`);
        }
      } catch (error) {
        console.error('Polling error:', error);
        // Don't stop polling on network errors — retry next tick
      }
    }, 3000);
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  showSuccess(mpesaReceipt, orderId) {
    document.getElementById('payment-status').innerHTML = `
      <div class="success-icon">✅</div>
      <h3>Payment Successful!</h3>
      <p>M-Pesa Receipt: <strong>${mpesaReceipt}</strong></p>
      <a href="/orders/${orderId}/confirmation" class="btn-primary">View Order Confirmation</a>
    `;
  }

  showError(message) {
    document.getElementById('payment-status').innerHTML = `
      <div class="error-icon">❌</div>
      <h3>Payment Failed</h3>
      <p>${message}</p>
      <button onclick="location.reload()" class="btn-secondary">Try Again</button>
    `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const payment = new MpesaPayment();

  document.getElementById('pay-btn').addEventListener('click', () => {
    const orderId = document.getElementById('order-id').value;
    const phone   = document.getElementById('phone-number').value;

    if (!phone || phone.length < 10) {
      alert('Please enter a valid phone number');
      return;
    }
    payment.initiatePayment(orderId, phone);
  });
});
```

---

## 16. Advanced Topics {#16-advanced}

### Idempotency

```python
class IdempotentSTKPush:
    """STK Push with built-in idempotency using Redis."""

    def __init__(self, auth_client, redis_client, stk_client):
        self.auth  = auth_client
        self.redis = redis_client
        self.stk   = stk_client

    def initiate(self, idempotency_key: str, phone: str, amount: int, reference: str) -> dict:
        """
        Initiate payment with idempotency protection.
        If this key was used before, return the cached result instead
        of initiating a new payment.
        """
        redis_key = f"idempotency:{idempotency_key}"
        cached    = self.redis.get(redis_key)

        if cached:
            return json.loads(cached)

        result = self.stk.initiate(phone, amount, reference)

        # Cache the result for 24 hours
        self.redis.setex(redis_key, 86400, json.dumps(result))

        return result
```

### Retry Mechanisms

```python
import time
from functools import wraps

def with_retry(max_attempts=3, backoff_factor=2, retryable_exceptions=(requests.Timeout, requests.ConnectionError)):
    """
    Decorator for automatic retry with exponential backoff.

    Use ONLY for read operations (status checks, balance queries).
    Do NOT use for payment initiation — retrying could cause duplicate charges.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    wait_time      = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

            raise last_exception
        return wrapper
    return decorator
```

### Queue-Based Payment Processing

```python
from celery import Celery

celery_app = Celery(
    "payments",
    broker  = "redis://localhost:6379/2",
    backend = "redis://localhost:6379/3",
)


@celery_app.task(bind=True, max_retries=3)
def process_stk_callback_task(self, payload: dict):
    """
    Process STK Push callback as a background task.
    Returns 200 to Daraja immediately; slow work (DB writes, emails,
    order fulfilment) happens in a worker process.
    """
    try:
        parsed = parse_stk_callback(payload)
        save_transaction_result(parsed)

        if parsed["success"]:
            fulfill_order.delay(parsed["checkout_request_id"])
            send_payment_receipt.delay(parsed["mpesa_receipt"], parsed["phone_number"])

    except Exception as exc:
        # Retry with exponential backoff: 60s, 120s, 240s
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@app.route("/callbacks/mpesa/stk", methods=["POST"])
def stk_callback():
    payload = request.get_json(force=True)
    process_stk_callback_task.delay(payload)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
```

### Payment Reconciliation

```python
class ReconciliationEngine:
    """End-of-day reconciliation to catch missed callbacks."""

    def __init__(self, stk_client: STKPush, status_client: TransactionStatus):
        self.stk    = stk_client
        self.status = status_client

    def run_daily_reconciliation(self, date: datetime) -> dict:
        start       = date.replace(hour=0,  minute=0,  second=0)
        end         = date.replace(hour=23, minute=59, second=59)

        unresolved = Transaction.query.filter(
            Transaction.created_at.between(start, end),
            Transaction.status == "pending"
        ).all()

        logger.info(f"Reconciliation: {len(unresolved)} pending on {date.date()}")

        reconciled_count = failed_count = 0

        for txn in unresolved:
            try:
                if txn.checkout_request_id:
                    result      = self.stk.query_status(txn.checkout_request_id)
                    result_code = result.get("ResultCode")

                    if result_code == "0":
                        txn.status           = "completed"
                        txn.reconcile_method = "daily_reconciliation"
                        txn.reconciled       = True
                        reconciled_count    += 1
                    elif result_code in ["1032", "1037", "1", "2001"]:
                        txn.status         = "failed"
                        txn.failure_reason = result.get("ResultDesc", "Failed during reconciliation")
                        failed_count      += 1

                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Reconciliation failed for txn {txn.id}: {e}")

        db.session.commit()

        report = {
            "date":                      str(date.date()),
            "total_checked":             len(unresolved),
            "reconciled_as_completed":   reconciled_count,
            "reconciled_as_failed":      failed_count,
            "still_pending":             len(unresolved) - reconciled_count - failed_count,
        }
        logger.info(f"Reconciliation complete: {report}")
        return report
```

### Microservices Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MICROSERVICES LAYOUT                         │
│                                                                 │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐   │
│  │  API Gateway  │    │  Auth Service │    │  Order Service│   │
│  │  (nginx/Kong) │    │  (tokens,     │    │  (orders,     │   │
│  │               │    │   sessions)   │    │   products)   │   │
│  └──────┬────────┘    └───────────────┘    └───────┬───────┘   │
│         │                                          │           │
│  ┌──────▼────────────────────────────────────────▼──────────┐  │
│  │                   Message Bus (RabbitMQ/Kafka)           │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│  ┌───────────────┐    ┌────▼──────────┐    ┌───────────────┐   │
│  │  STK Push     │    │  Callback     │    │  Reconcile    │   │
│  │  Service      │    │  Processor    │    │  Service      │   │
│  │  (initiates)  │    │  (webhooks)   │    │  (cron jobs)  │   │
│  └───────────────┘    └───────────────┘    └───────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 17. Common Errors and Troubleshooting {#17-errors}

### Error Reference Table

| Error Code | Name | Cause | Solution |
|---|---|---|---|
| `404.001.03` | Invalid Access Token | Token expired or malformed | Regenerate token |
| `500.001.1001` | Unable to lock subscriber | Subscriber is in another active STK session | Wait 30s, retry |
| `400.002.02` | Bad Request | Missing or invalid request parameters | Validate payload |
| `1032` | Request Cancelled | Customer cancelled the prompt | Prompt user to retry |
| `1037` | Timeout | Customer didn't respond in time | Prompt user to retry |
| `1` | Insufficient Funds | Customer M-Pesa balance too low | Inform customer |
| `2001` | Wrong PIN | Customer entered incorrect PIN | Inform customer (max 3 tries) |
| `17` | Risk Management | Risk threshold exceeded | Customer contacts Safaricom |

### Authentication Failures

```python
# Symptom: Getting 404.001.03 on every request
# Cause: Token expired; not refreshing before use

# Wrong:
token = get_token_once_at_startup()   # expires after 1 hour

# Correct:
def make_daraja_request():
    token = auth.get_access_token()   # always fetch (uses cache if valid)
    # ...

# Symptom: Getting 401 from the token endpoint
# Debug:
import base64
key         = "your_consumer_key"
secret      = "your_consumer_secret"
encoded     = base64.b64encode(f"{key}:{secret}".encode()).decode()
print(f"Basic {encoded}")
# Paste into Postman and test manually
```

### Callback Issues

```python
# Problem: Callbacks not being received
# Checklist:
# 1. Is your callback URL publicly accessible? (not localhost)
# 2. Is it HTTPS with a valid certificate?
# 3. In production: is the URL pre-registered in the Daraja portal?
# 4. Is your server returning HTTP 200?

# Debug — create a logging endpoint and use ngrok:
@app.route("/callbacks/mpesa/debug", methods=["GET", "POST"])
def debug_callback():
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Body: {request.get_data()}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Debug accepted"}), 200
```

### Timeout Errors

```python
def make_request_with_fallback(url, payload, headers, max_attempts=2):
    for attempt in range(max_attempts):
        try:
            return requests.post(url, json=payload, headers=headers, timeout=30).json()
        except requests.Timeout:
            if attempt < max_attempts - 1:
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(2)
            else:
                logger.error("All attempts timed out")
                raise
```

### Sandbox Limitations

| Limitation | Details |
|---|---|
| Test phone numbers only | STK Push works with `254708374149` only in sandbox |
| No real money | All transactions are simulated |
| Any callback URL | Production requires pre-registered URLs |
| Simulated delays | Callbacks may come faster or slower than production |
| Transaction limits | Sandbox allows any amount; production minimum is KES 1 |

```python
# Common sandbox mistake: using a real phone number
# Wrong:
result = stk.initiate(phone_number="0712345678", amount=100, ...)  # "Invalid MSISDN"

# Correct — in sandbox always use the official test number:
SANDBOX_TEST_PHONE = "254708374149"
result = stk.initiate(phone_number=SANDBOX_TEST_PHONE, amount=100, ...)
```

### Invalid Shortcode / Credential Errors

```bash
# Error: "The initiator information is invalid"
# Cause: Initiator name doesn't match what's registered for your shortcode,
#        OR the sandbox B2C certificate has expired.

# Sandbox defaults:
# Shortcode:      174379
# Initiator Name: testapi
# Passkey:        bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919

# If B2C was working and suddenly stops: download a fresh sandbox certificate
# from the Daraja portal (sandbox certs expire periodically).
```

---

## 18. Production Readiness Checklist {#18-checklist}

### 🔐 Security

- [ ] All credentials stored in environment variables or secrets manager
- [ ] `.env` files in `.gitignore`; no credentials in Git history
- [ ] Callback IP validation implemented (with current Safaricom IP list verified)
- [ ] Callback payload schema validation implemented
- [ ] HTTPS enforced on all callback URLs
- [ ] Replay attack protection implemented (with correct timezone handling)
- [ ] Duplicate transaction prevention with Redis (SHA-256 fingerprint)
- [ ] Rate limiting on callback endpoints
- [ ] Input validation on all endpoints (phone number format, amount range)
- [ ] SQL injection prevention (ORM parameterized queries)

### 🔄 Reliability

- [ ] Token caching with auto-refresh and Redis lock (race-condition safe)
- [ ] All Daraja requests have timeouts configured
- [ ] Error handling for all API calls (network, HTTP, parsing)
- [ ] Callback processing is idempotent (duplicate callbacks handled)
- [ ] HTTP 200 returned immediately from callback endpoints
- [ ] Transaction records created BEFORE initiating STK Push
- [ ] Reconciliation job running every 30–60 minutes
- [ ] Background task queue for callback processing (Celery/Bull)

### 📊 Monitoring

- [ ] Structured JSON logging configured
- [ ] Log aggregation set up (CloudWatch, Elasticsearch, etc.)
- [ ] Payment success rate metrics tracked
- [ ] Alerts configured for: success rate drops, pending transaction backlog, auth failures, volume spikes, low B2C balance
- [ ] Uptime monitoring for callback endpoints
- [ ] Error tracking (Sentry, Rollbar)

### 📦 Database

- [ ] All critical indexes created
- [ ] Raw callback payloads stored in `callback_logs`
- [ ] Audit trail table populated on state changes
- [ ] Database backups configured and tested
- [ ] Connection pooling configured

### 🚀 Deployment

- [ ] Safaricom go-live application approved
- [ ] Production shortcode, passkey, and credentials obtained
- [ ] **All production callback URLs pre-registered in Daraja portal**
- [ ] Production SSL certificates installed and tested
- [ ] Environment variables updated for production
- [ ] Deployment tested with a real small transaction (KES 1)
- [ ] B2C production certificate downloaded and deployed

### 📋 Compliance

- [ ] Customer consent collected for M-Pesa transactions
- [ ] Privacy policy updated to mention M-Pesa processing
- [ ] Receipt/confirmation sent after successful payment
- [ ] Refund policy documented and reversal flow tested
- [ ] Transaction records retained for minimum 7 years (KRA requirement)

### 👤 User Experience

- [ ] Real-time payment status shown to customer (polling implemented)
- [ ] Clear instructions: "Check your phone for PIN prompt"
- [ ] Helpful error messages for common failures
- [ ] Retry option on failure
- [ ] Payment confirmation page with M-Pesa receipt number
- [ ] Support contact provided if payment is stuck

---

## Appendix: Quick Reference

### Sandbox Credentials

```
Base URL:     https://sandbox.safaricom.co.ke
Shortcode:    174379
Passkey:      bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
Test Phone:   254708374149
Initiator:    testapi
```

> **Reminder:** These values are Safaricom's publicly documented sandbox test credentials. Your production values will be unique to your business and provided during go-live approval. Never use sandbox values in production.

### Key Endpoints

```
Token:        GET  /oauth/v1/generate?grant_type=client_credentials
STK Push:     POST /mpesa/stkpush/v1/processrequest
STK Query:    POST /mpesa/stkpushquery/v1/query
C2B Register: POST /mpesa/c2b/v1/registerurl
B2C:          POST /mpesa/b2c/v1/paymentrequest
Reversal:     POST /mpesa/reversal/v1/request
Tx Status:    POST /mpesa/transactionstatus/v1/query
Balance:      POST /mpesa/accountbalance/v1/query
```

### Result Codes Summary

```
0     = Success
1     = Insufficient balance
17    = Risk management rejection
1001  = System error (retry)
1032  = Cancelled by user
1037  = Request timed out
2001  = Wrong PIN
500.001.1001 = Subscriber locked in another STK session (wait 30s, retry)
```

### Required Callback Response (always return this)

```json
{"ResultCode": 0, "ResultDesc": "Accepted"}
```

---

# The Complete M-Pesa Daraja API Integration Guide
**From Sandbox to Production — A Practical, Production-Focused Course**

*Guide version: 2024 | For the latest Daraja documentation, visit [developer.safaricom.co.ke](https://developer.safaricom.co.ke)*

> **Who this guide is for:** Developers with basic programming knowledge (Python or JavaScript) who want to integrate M-Pesa payments into real-world applications. No prior Daraja experience needed.

---

