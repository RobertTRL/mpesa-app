from http.server import BaseHTTPRequestHandler
import json
import sys
import os
from lib.accesstoken import AccessToken
from lib.stkpush import STKPush

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        phone = body.get("phone")
        amount = body.get("amount")

        if not phone or not amount:
            self._respond(400, {"success": False, "error": "phone and amount are required"})
            return
        try:
            auth = AccessToken()
            push = STKPush(auth)
            result = push.initiate(
                phone_number=phone,
                amount=int(amount),
                account_reference="BOBTOROITICH",
                transaction_description="Payment"
            )
            self._respond(200 if result["success"] else 400, result)

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