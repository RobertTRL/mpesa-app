from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.accesstoken import AccessToken

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        amount = body.get("amount")

        if not amount:
            self._respond(400, {"success": False, "error": "amount is required"})
            return

        try:
            auth = AccessToken()
            token = auth.get_access_token()

            payload = {
                "MerchantName": "BOBTOROITICH",      # max 20 chars
                "RefNo":        "Payment",            # max 12 chars
                "Amount":       str(int(amount)),
                "TrxCode":      "BG",                 # Buy Goods
                "CPI":          os.getenv("PRODUCTION_TILL_NUMBER"),
            }

            res = requests.post(
                "https://api.safaricom.co.ke/mpesa/qrcode/v1/generate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                timeout=30,
            )
            data = res.json()

            if data.get("ResponseCode") == "00":
                self._respond(200, {"success": True, "qr": data["QRCode"]})
            else:
                self._respond(400, {
                    "success": False,
                    "error": data.get("ResponseDescription", "QR generation failed"),
                })

        except Exception as e:
            self._respond(500, {"success": False, "error": str(e)})

    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()