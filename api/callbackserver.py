from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/callback":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            print("\n📲 Callback received!")
            print(json.dumps(data, indent=2))
            
            # Respond with 200 so Safaricom knows you got it
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    # Suppress default request logs (optional)
    def log_message(self, format, *args):
        pass

server = HTTPServer(("0.0.0.0", 5000), CallbackHandler)
print("✅ Listening for callbacks on port 5000...")
server.serve_forever()