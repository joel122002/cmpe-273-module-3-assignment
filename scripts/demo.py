"""Run both transports and print success, timeout/deadline, and recovery evidence."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PYTHON = sys.executable
children = []


def start(module, *args, delay="0"):
    env = os.environ.copy()
    env["INVENTORY_DELAY_SECONDS"] = delay
    env.setdefault("REST_TIMEOUT_SECONDS", "1")
    env.setdefault("GRPC_DEADLINE_SECONDS", "1")
    proc = subprocess.Popen(
        [PYTHON, "-m", module, *args], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    children.append(proc)
    time.sleep(0.5)
    if proc.poll() is not None:
        raise RuntimeError(f"{module} exited during startup")
    return proc


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    children.remove(proc)


def rest_order():
    payload = json.dumps({"item_id": "book", "quantity": 2}).encode()
    req = Request("http://127.0.0.1:8000/orders", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=4) as response:
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def run_rest():
    inventory = start("order_inventory.rest_inventory")
    order = start("order_inventory.rest_order")
    try:
        status, body = rest_order()
        print(f"REST success: HTTP {status}; {body}")
        stop(inventory)
        inventory = start("order_inventory.rest_inventory", delay="3")
        status, body = rest_order()
        print(f"REST delayed inventory: HTTP {status}; {body}")
        stop(inventory)
        inventory = start("order_inventory.rest_inventory")
        status, _ = rest_order()
        print(f"REST Order Service: still running (pid {order.pid}); subsequent request returned HTTP {status}")
    finally:
        for proc in (order, inventory):
            if proc in children:
                stop(proc)


def grpc_call():
    import grpc
    from order_inventory import inventory_pb2, inventory_pb2_grpc

    channel = grpc.insecure_channel("127.0.0.1:50052")
    stub = inventory_pb2_grpc.OrderServiceStub(channel)
    try:
        response = stub.PlaceOrder(inventory_pb2.OrderRequest(item_id="book", quantity=2), timeout=4)
        return f"accepted={response.accepted} message={response.message}"
    except grpc.RpcError as exc:
        return f"{exc.code().name}: {exc.details()}"
    finally:
        channel.close()


def run_grpc():
    inventory = start("order_inventory.grpc_services", "inventory")
    order = start("order_inventory.grpc_services", "order")
    try:
        print(f"gRPC success: {grpc_call()}")
        stop(inventory)
        inventory = start("order_inventory.grpc_services", "inventory", delay="3")
        print(f"gRPC delayed inventory: {grpc_call()}")
        stop(inventory)
        inventory = start("order_inventory.grpc_services", "inventory")
        print(f"gRPC Order Service: still running (pid {order.pid}); subsequent call returned {grpc_call()}")
    finally:
        for proc in (order, inventory):
            if proc in children:
                stop(proc)


try:
    run_rest()
    run_grpc()
finally:
    for proc in list(children):
        stop(proc)
