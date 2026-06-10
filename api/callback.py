from http.server import BaseHTTPRequestHandler
import json
import os
import psycopg2

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # ── 1. Read the request body ──────────────────────────────
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            # ── 2. Parse the JSON payload ─────────────────────────
            data = json.loads(body)
            stk_callback = data["Body"]["stkCallback"]

            result_code         = stk_callback["ResultCode"]
            result_desc         = stk_callback["ResultDesc"]
            checkout_request_id = stk_callback["CheckoutRequestID"]

            # ── 3. Extract payment details (only on success) ──────
            amount, mpesa_code, phone = None, None, None

            if result_code == 0:
                items = stk_callback["CallbackMetadata"]["Item"]
                metadata = {item["Name"]: item.get("Value") for item in items}
                amount     = metadata.get("Amount")
                mpesa_code = metadata.get("MpesaReceiptNumber")
                phone      = metadata.get("PhoneNumber")

            # ── 4. Save to Supabase ───────────────────────────────
            conn = get_db()
            cur  = conn.cursor()
            cur.execute("""
                INSERT INTO mpesa_payments (
                    checkout_request_id,
                    result_code,
                    result_desc,
                    amount,
                    mpesa_receipt,
                    phone
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (checkout_request_id) DO NOTHING
            """, (
                checkout_request_id,
                result_code,
                result_desc,
                amount,
                mpesa_code,
                str(phone) if phone else None
            ))
            conn.commit()
            cur.close()
            conn.close()

            print(f"[OK] Saved payment — Code: {result_code}, Receipt: {mpesa_code}, Amount: {amount}, Phone: {phone}")

        except Exception as e:
            print(f"[ERROR] Failed to process callback: {e}")

        # ── 5. Always return 200 to Safaricom ─────────────────────
        # If you don't, Safaricom will retry the callback repeatedly
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        }).encode())