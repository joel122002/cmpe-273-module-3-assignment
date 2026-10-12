# Order and Inventory Services: REST and gRPC (Python)

This repository implements the same order check using two transports. In each version, the Order Service accepts an item and quantity and asks the Inventory Service whether enough stock exists. The sample inventory contains 10 books, 25 pens, and 5 notebooks. Both Inventory Services support a configurable artificial delay for demonstrating downstream timeouts.

## Setup

Requires Python 3.10 or newer. In PowerShell, from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Generate the gRPC Python bindings after installing dependencies:

```powershell
.\scripts\generate_proto.ps1
```

## REST version

Open two PowerShell terminals from the repository root. Start Inventory Service in the first and Order Service in the second:

```powershell
python -m order_inventory.rest_inventory
```

```powershell
python -m order_inventory.rest_order
```

Order Service accepts `POST /orders` with JSON and calls `POST /inventory/check` with JSON. A successful order returns HTTP 201, insufficient stock returns HTTP 409, invalid input returns HTTP 400, and an inventory timeout returns HTTP 504. The downstream HTTP timeout defaults to 1 second and can be changed with `REST_TIMEOUT_SECONDS`.

Successful request:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/orders -H "Content-Type: application/json" -d '{"item_id":"book","quantity":2}'
```

Successful response:

```text
HTTP/1.0 201 Created
Content-Type: application/json

{"accepted": true, "available": true, "message": "book: 2 available"}
```

## gRPC version

The service and message definitions are in [`inventory.proto`](inventory.proto). Start Inventory Service and Order Service in separate terminals:

```powershell
python -m order_inventory.grpc_services inventory
```

```powershell
python -m order_inventory.grpc_services order
```

In another terminal, call Order Service:

```powershell
python -m order_inventory.grpc_client
```

Successful gRPC request/response (the client sends `item_id="book"`, `quantity=2`):

```text
PlaceOrder(OrderRequest(item_id="book", quantity=2))
accepted=True message=book: 2 available
```

The Order Service gives its Inventory Service call a 1 second deadline (`GRPC_DEADLINE_SECONDS`). An unavailable item or insufficient quantity uses `FAILED_PRECONDITION`; an exceeded downstream deadline uses `DEADLINE_EXCEEDED`.

## Slow Inventory failure demonstrations

Stop and restart the inventory process with a 3 second delay. The Order Service remains unchanged and running. In PowerShell, set the variable in the terminal that starts the Inventory Service:

```powershell
$env:INVENTORY_DELAY_SECONDS = "3"
python -m order_inventory.rest_inventory
```

In another terminal POST the same request. It returns HTTP 504 after the configured 1 second timeout:

```text
HTTP/1.0 504 Gateway Timeout
{"error": "inventory request timed out after 1s"}
```

The REST Order Service terminal logs the 504 and continues serving requests; confirm it is still listening by sending another request after restoring the inventory to zero delay.

For gRPC, stop the inventory process and start it with the same delay:

```powershell
$env:INVENTORY_DELAY_SECONDS = "3"
python -m order_inventory.grpc_services inventory
```

Call the Order Service with `python -m order_inventory.grpc_client`. It reports the deadline error cleanly:

```text
gRPC error: DEADLINE_EXCEEDED: inventory check exceeded the order deadline
```

Order Service logs the deadline expiration and stays available. Re-run the client after setting `INVENTORY_DELAY_SECONDS` to `0` for another successful order.

### Captured execution evidence

The [captured execution transcript](evidence/demo-output.txt) records a successful REST request, a delayed inventory timeout, and a later successful request handled by the same Order Service process. The gRPC transcript similarly shows success, an exceeded deadline while Inventory is delayed, and success again after removing the delay. Reproduce it with:

```text
python scripts/demo.py
```

## REST vs. gRPC comparison

REST was straightforward to inspect because requests and responses are plain JSON over familiar HTTP endpoints, and HTTP status codes communicate success, invalid input, and timeout outcomes. gRPC required a `.proto` contract and generated Python bindings, so there was more setup before making a call. Once generated, the gRPC request and response types were explicit and the client deadline and failure status were part of the RPC interface. Both transports handled the delayed Inventory Service without terminating the Order Service. For this small example REST is easier to explore manually, while gRPC provides a strongly typed contract and a direct `DEADLINE_EXCEEDED` status for service-to-service calls.

