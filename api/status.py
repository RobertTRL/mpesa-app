from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import psycopg2

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        checkout_id = query.get("id", [None])[0]
        if not checkout_id:
            self._respond(400, {"error": "id parameter required"})
            return
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"])
            cur = conn.cursor()
            cur.execute("""
                SELECT result_code, result_desc, amount, mpesa_receipt, phone
                FROM mpesa_payments
                WHERE checkout_request_id = %s
            """, (checkout_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                self._respond(200, {
                    "found": True,
                    "resultCode": row[0],
                    "resultDesc": row[1],
                    "amount": float(row[2]) if row[2] else None,
                    "receipt": row[3],
                    "phone": row[4],
                })
            else:
                self._respond(200, {"found": False})
        except Exception as e:
            self._respond(500, {"error": str(e)})
    def _respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()