import grpc

from . import inventory_pb2, inventory_pb2_grpc


def main():
    channel = grpc.insecure_channel("127.0.0.1:50052")
    stub = inventory_pb2_grpc.OrderServiceStub(channel)
    try:
        reply = stub.PlaceOrder(inventory_pb2.OrderRequest(item_id="book", quantity=2), timeout=3)
        print(f"accepted={reply.accepted} message={reply.message}")
    except grpc.RpcError as exc:
        print(f"gRPC error: {exc.code().name}: {exc.details()}")


if __name__ == "__main__":
    main()
