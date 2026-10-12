$ErrorActionPreference = "Stop"
python -m grpc_tools.protoc -I . --python_out=order_inventory --grpc_python_out=order_inventory inventory.proto
(Get-Content order_inventory/inventory_pb2_grpc.py -Raw).Replace("import inventory_pb2 as inventory__pb2", "from . import inventory_pb2 as inventory__pb2") | Set-Content order_inventory/inventory_pb2_grpc.py
