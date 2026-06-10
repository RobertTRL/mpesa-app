from dotenv import load_dotenv
import os
import requests
from datetime import datetime
import base64
import time
import uuid

load_dotenv()

CONSUMER_KEY = os.getenv("PRODUCTION_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("PRODUCTION_CONSUMER_SECRET")
PASSKEY = os.getenv("PRODUCTION_PASSKEY")
CALLBACK_URL = os.getenv("PRODUCTION_CALLBACK_URL")
SHORTCODE = os.getenv("PRODUCTION_SHORTCODE")
BASE_URL = os.getenv("PRODUCTION_BASE_URL")
TEST_NUMBER = "254791154865"
TILL_NUMBER = os.getenv("PRODUCTION_TILL_NUMBER")

# ─── Step 2: Get an OAuth access token ────────────────────────────────────────
# Daraja uses OAuth 2.0 Client Credentials. You encode your key and secret
# as Base64(key:secret) and send them as HTTP Basic Auth.

print("Step 1: Fetching access token...")

credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

token_response = requests.get(
    f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials", # token_url
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
    "TransactionType":   "CustomerBuyGoodsOnline",
    "Amount":            1,                  # KES 1 for testing
    "PartyA":            TEST_NUMBER,         # who is paying
    "PartyB":            TILL_NUMBER,          # who is being paid (your shortcode)
    "PhoneNumber":       TEST_NUMBER,         # who gets the PIN prompt
    "CallBackURL":       CALLBACK_URL,       # where Daraja posts the result
    "AccountReference":  str(uuid.uuid4())[:12],         # shown to the customer (max 12 chars)
    "TransactionDesc":   "Test payment",     # brief description (max 13 chars)
}

stk_response = requests.post(
    f"{BASE_URL}/mpesa/stkpush/v1/processrequest", # stk_push_url
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

print("Waiting 10 seconds for Safaricom to process...")
time.sleep(30)

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
        f"{BASE_URL}/mpesa/stkpushquery/v1/query", #query_url
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
    print(f"  Raw query response: {query_data}")

