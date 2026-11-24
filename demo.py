#!/usr/bin/env python3
"""PyShoppingCart Standalone Scripted Demo.

Demonstrates:
  - Domain models, cart operations, stock validation, checkout, and JSON persistence.
  - Discount policies, custom generators/iterators, decorators, and pure functional reporting.
  - Multi-threaded race condition on last stock unit with threading.Lock synchronization.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

# Ensure src/ is on python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pyshoppingcart.exceptions import InsufficientStockError
from pyshoppingcart.models import Customer, Product
from pyshoppingcart.persistence import JsonStoreRepository
from pyshoppingcart.pricing import BulkThresholdDiscount, PercentageDiscount, PricingEngine
from pyshoppingcart.reporting import OrderBatchIterator, generate_order_summary, low_stock_scanner
from pyshoppingcart.store import Store
from pyshoppingcart.utils.formatters import cents_to_usd


def header(title: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def step(title: str) -> None:
    print(f"\n---> {title}")


def main() -> None:
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    header("PyShoppingCart - Full Architecture & Concurrency Demo")

    # =========================================================================
    # Store Setup & Catalog Seeding
    # =========================================================================
    step("Initializing Store & Seeding Catalog (Integer Cents Currency)")
    pricing_engine = PricingEngine(
        policies=[
            # $15.00 off orders over $100.00
            BulkThresholdDiscount(threshold_cents=10000, discount_cents=1500, name_label="Bulk Order Special")
        ]
    )
    temp_json = Path("demo_store_state.json")
    if temp_json.exists():
        temp_json.unlink()

    store = Store(name="PyShoppingCart Main Store", persistence_file=temp_json, pricing_engine=pricing_engine)

    # Add products with prices strictly in integer cents (no floats)
    p_laptop = Product("PROD-01", "Developer Laptop", 120000, 5, "Computers")  # $1,200.00
    p_mouse = Product("PROD-02", "Wireless Mouse", 3500, 20, "Peripherals")     # $35.00
    p_stand = Product("PROD-03", "Laptop Stand", 4500, 2, "Accessories")        # $45.00
    p_gpu = Product("PROD-04", "Rare Collector GPU", 80000, 1, "Hardware")     # $800.00 (Only 1 in stock!)

    for p in [p_laptop, p_mouse, p_stand, p_gpu]:
        store.add_product(p)
        print(f"  [Catalog] {p}")

    # Register customers
    alice = Customer("CUST-ALICE", "Alice Smith", "alice@example.com")
    bob = Customer("CUST-BOB", "Bob Martin", "bob@example.com")
    charlie = Customer("CUST-CHARLIE", "Charlie Brown", "charlie@example.com")
    store.register_customer(alice)
    store.register_customer(bob)
    store.register_customer(charlie)
    print(f"  [Registered] {alice}")
    print(f"  [Registered] {bob}")
    print(f"  [Registered] {charlie}")

    # =========================================================================
    # Cart Operations & Stock Limit Validation
    # =========================================================================
    step("Cart Operations & Stock Limits Validation")
    cart_alice = store.get_or_create_cart(alice.id)
    store.add_to_cart(alice.id, p_laptop.id, quantity=1)
    store.add_to_cart(alice.id, p_mouse.id, quantity=2)
    print(f"  Alice's Cart: {cart_alice}")
    for item in cart_alice:
        print(f"    - {item.product_name} x {item.quantity} = {cents_to_usd(item.subtotal_cents)}")

    # Test stock limits rejection: Laptop has 5 in stock; adding 10 more must fail
    print("\n  Testing stock limit enforcement (Requesting 10 more Laptops when only 5 exist):")
    try:
        store.add_to_cart(alice.id, p_laptop.id, quantity=10)
        print("  ERROR: Expected InsufficientStockError but succeeded!")
    except InsufficientStockError as exc:
        print(f"  [REJECTED AS EXPECTED] {exc}")

    # =========================================================================
    # Pricing & Discount Stacking Engine
    # =========================================================================
    step("Pricing Engine & Discount Stacking Policy")
    # Subtotal: 1 Laptop ($1200) + 2 Mice ($70) = $1270 (127000 cents)
    # BulkThresholdDiscount ($15 off over $100) -> balance: 125500 cents
    # PercentageDiscount (10% off promo) -> 10% of 125500 = 12550 cents
    # Final Total: 125500 - 12550 = 112950 cents ($1,129.50)
    promo = PercentageDiscount(code="SPRING10", percentage=10)
    pricing = store.pricing_engine.calculate_pricing(cart_alice, extra_policies=[promo])
    print(f"  Subtotal:        {cents_to_usd(pricing.subtotal_cents)}")
    print(f"  Total Discounts: -{cents_to_usd(pricing.discount_cents)}")
    for note in pricing.discount_notes:
        print(f"    * {note}")
    print(f"  Final Total:     {cents_to_usd(pricing.total_cents)}")

    # =========================================================================
    # Atomic Checkout Flow
    # =========================================================================
    step("Performing Atomic Checkout for Alice")
    initial_laptop_stock = store.get_product(p_laptop.id).stock
    order_alice = store.checkout(alice.id, extra_policies=[promo])
    print(f"  {order_alice}")
    print(f"  Temporary Cart after checkout: {cart_alice} (is_empty: {cart_alice.is_empty})")
    print(f"  Laptop Stock: Before={initial_laptop_stock}, After={store.get_product(p_laptop.id).stock}")

    # =========================================================================
    # JSON Persistence
    # =========================================================================
    step("JSON Persistence Roundtrip (Save & Reload)")
    store.save_state()
    print(f"  State saved to '{temp_json}'. Size: {temp_json.stat().st_size} bytes.")

    # Create fresh store and reload state
    reloaded_store = Store(name="Reloaded Store", persistence_file=temp_json)
    reloaded_store.load_state()
    print(f"  Reloaded Products count: {len(reloaded_store.list_products())}")
    print(f"  Reloaded Orders count:   {len(reloaded_store.list_orders())}")
    reloaded_order = reloaded_store.get_order(order_alice.id)
    print(f"  Verified Persisted Order: {reloaded_order}")

    # Place a second order for Bob to enrich order history
    store.add_to_cart(bob.id, p_stand.id, quantity=1)
    order_bob = store.checkout(bob.id)
    print(f"  Placed Bob's order: {order_bob}")

    # =========================================================================
    # Custom Iterators & Generators
    # =========================================================================
    step("Custom Generator (Low-Stock Scanner) & Iterator (Order Batching)")
    print("  Low-Stock Scanner (threshold <= 5 units):")
    for prod in low_stock_scanner(store.list_products(), threshold=5):
        print(f"    - Alert: '{prod.name}' has only {prod.stock} unit(s) left!")

    print("\n  OrderBatchIterator (streaming orders in batch sizes of 1):")
    batch_iter = OrderBatchIterator(store.list_orders(), batch_size=1)
    for i, batch in enumerate(batch_iter, 1):
        print(f"    Batch {i}: {[o.id for o in batch]}")

    # =========================================================================
    # Pure Functional Order Analytics Report
    # =========================================================================
    step("Pure Functional Order History Report (map / filter / reduce)")
    summary = generate_order_summary(store.list_orders())
    print(summary)

    # =========================================================================
    # Concurrency & Race Condition Acceptance Test
    # =========================================================================
    step("Concurrency Scenario: Racing 5 Threads for the Last Remaining GPU")
    print("  Target Product: 'Rare Collector GPU' (Initial stock = 1 unit)")
    assert store.get_product(p_gpu.id).stock == 1

    # Prepare carts for 5 concurrent shoppers
    competitors = [
        Customer(f"RACER-{i}", f"Shopper {i}", f"shopper{i}@race.com")
        for i in range(1, 6)
    ]
    for c in competitors:
        store.register_customer(c)
        store.add_to_cart(c.id, p_gpu.id, quantity=1)

    successful_checkouts: list[str] = []
    failed_checkouts: list[tuple[str, str]] = []
    barrier = threading.Barrier(len(competitors))

    def race_worker(customer_id: str) -> None:
        # Synchronize thread start at barrier so all threads race concurrently
        barrier.wait()
        try:
            # Checkout protected by Store's threading.Lock
            order = store.checkout(customer_id, use_lock=True, simulate_race_delay=0.002)
            successful_checkouts.append(customer_id)
        except InsufficientStockError as err:
            failed_checkouts.append((customer_id, err.__class__.__name__))

    threads = [
        threading.Thread(target=race_worker, args=(c.id,), name=f"Thread-{c.id}")
        for c in competitors
    ]

    print(f"  Launching {len(threads)} concurrent threads racing simultaneously...")
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_stock = store.get_product(p_gpu.id).stock
    print(f"\n  Concurrency Results:")
    print(f"    - Successful Checkouts count: {len(successful_checkouts)} -> Winner: {successful_checkouts}")
    print(f"    - Cleanly Rejected count:    {len(failed_checkouts)} -> Rejections: {failed_checkouts}")
    print(f"    - Final Product Stock:       {final_stock}")

    # Acceptance Assertions
    assert len(successful_checkouts) == 1, f"Expected exactly 1 winner, got {len(successful_checkouts)}"
    assert len(failed_checkouts) == 4, f"Expected 4 clean rejections, got {len(failed_checkouts)}"
    assert final_stock == 0, f"Stock should be exactly 0, got {final_stock}"

    print("\n  [VERIFIED] Acceptance Criteria Satisfied:")
    print("    * At most ONE concurrent checkout succeeded for the last item.")
    print("    * All other threads received InsufficientStockError.")
    print("    * Product stock remained strictly non-negative (>= 0).")
    print("    * Zero overselling occurred under concurrent load.")

    # Cleanup demo state
    if temp_json.exists():
        temp_json.unlink()

    header("Demo Completed Successfully with Zero Errors!")


if __name__ == "__main__":
    main()
