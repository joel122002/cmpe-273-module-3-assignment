import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def inventory_url():
    return os.getenv("REST_INVENTORY_URL", "http://127.0.0.1:8001/inventory/check")


def inventory_timeout():
    return float(os.getenv("REST_TIMEOUT_SECONDS", "1.0"))


class OrderHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/orders":
            self.send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            order = json.loads(self.rfile.read(length))
            item_id, quantity = order.get("item_id", ""), int(order.get("quantity", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "expected JSON with item_id and integer quantity"})
            return
        body = json.dumps({"item_id": item_id, "quantity": quantity}).encode()
        request = Request(inventory_url(), data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=inventory_timeout()) as response:
                result = json.loads(response.read())
                status = 201 if result.get("available") else 409
                self.send_json(status, {"accepted": status == 201, **result})
        except HTTPError as exc:
            if exc.code == 409:
                result = json.loads(exc.read())
                self.send_json(409, {"accepted": False, **result})
            else:
                self.send_json(502, {"error": f"inventory returned HTTP {exc.code}"})
        except TimeoutError:
            self.send_json(504, {"error": f"inventory request timed out after {inventory_timeout():g}s"})
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                self.send_json(504, {"error": f"inventory request timed out after {inventory_timeout():g}s"})
            else:
                self.send_json(502, {"error": f"inventory unavailable: {exc.reason}"})

    def send_json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[REST order] {self.address_string()} - {fmt % args}", flush=True)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), OrderHandler)
    print("REST Order Service listening on http://127.0.0.1:8000", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
