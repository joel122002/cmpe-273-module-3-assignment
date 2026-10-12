import os
import time
from concurrent import futures

import grpc

from . import inventory_pb2, inventory_pb2_grpc
from .common import check_stock, inventory_delay

GRPC_DEADLINE_SECONDS = float(os.getenv("GRPC_DEADLINE_SECONDS", "1.0"))


class InventoryServicer(inventory_pb2_grpc.InventoryServiceServicer):
    def CheckInventory(self, request, context):
        time.sleep(inventory_delay())
        available, message = check_stock(request.item_id, request.quantity)
        if not available:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, message)
        return inventory_pb2.InventoryReply(available=True, message=message)


class OrderServicer(inventory_pb2_grpc.OrderServiceServicer):
    def __init__(self, inventory_stub):
        self.inventory_stub = inventory_stub

    def PlaceOrder(self, request, context):
        try:
            reply = self.inventory_stub.CheckInventory(
                inventory_pb2.InventoryRequest(item_id=request.item_id, quantity=request.quantity),
                timeout=GRPC_DEADLINE_SECONDS,
            )
            return inventory_pb2.OrderReply(accepted=True, message=reply.message)
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, exc.details())
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                print(f"[gRPC order] Inventory deadline exceeded after {GRPC_DEADLINE_SECONDS:g}s", flush=True)
                context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "inventory check exceeded the order deadline")
            context.abort(grpc.StatusCode.UNAVAILABLE, f"inventory call failed: {exc.details()}")


def serve_inventory():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    print("gRPC Inventory Service listening on 127.0.0.1:50051", flush=True)
    server.wait_for_termination()


def serve_order():
    channel = grpc.insecure_channel("127.0.0.1:50051")
    inventory_stub = inventory_pb2_grpc.InventoryServiceStub(channel)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_OrderServiceServicer_to_server(OrderServicer(inventory_stub), server)
    server.add_insecure_port("127.0.0.1:50052")
    server.start()
    print("gRPC Order Service listening on 127.0.0.1:50052", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in {"inventory", "order"}:
        raise SystemExit("usage: python -m order_inventory.grpc_services inventory|order")
    (serve_inventory if sys.argv[1] == "inventory" else serve_order)()
