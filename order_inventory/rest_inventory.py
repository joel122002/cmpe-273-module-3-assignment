import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .common import check_stock, inventory_delay


class InventoryHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/inventory/check":
            self.send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            item_id, quantity = payload.get("item_id", ""), int(payload.get("quantity", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "expected JSON with item_id and integer quantity"})
            return
        time.sleep(inventory_delay())
        available, message = check_stock(item_id, quantity)
        self.send_json(200 if available else 409, {"available": available, "message": message})

    def send_json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[REST inventory] {self.address_string()} - {fmt % args}", flush=True)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8001), InventoryHandler)
    print("REST Inventory Service listening on http://127.0.0.1:8001", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
