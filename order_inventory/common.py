import os

INVENTORY = {"book": 10, "pen": 25, "notebook": 5}


def inventory_delay() -> float:
    """Delay each inventory check; set INVENTORY_DELAY_SECONDS for failure demos."""
    try:
        return max(0.0, float(os.getenv("INVENTORY_DELAY_SECONDS", "0")))
    except ValueError:
        return 0.0


def check_stock(item_id: str, quantity: int) -> tuple[bool, str]:
    if not item_id:
        return False, "item_id is required"
    if quantity <= 0:
        return False, "quantity must be greater than zero"
    available = INVENTORY.get(item_id, 0)
    if available < quantity:
        return False, f"{item_id} has {available} available; {quantity} requested"
    return True, f"{item_id}: {quantity} available"
