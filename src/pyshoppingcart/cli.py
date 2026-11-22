"""Interactive terminal CLI for PyShoppingCart.

Pure Python command-line menu interface (no GUI, no web framework).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyshoppingcart.exceptions import (
    DomainError,
    EntityNotFoundError,
    InsufficientStockError,
    PyShoppingCartError,
)
from pyshoppingcart.models import Customer, Product
from pyshoppingcart.pricing import BulkThresholdDiscount, PercentageDiscount, PricingEngine
from pyshoppingcart.reporting import generate_order_summary, low_stock_scanner
from pyshoppingcart.store import Store
from pyshoppingcart.utils.formatters import cents_to_usd, usd_to_cents


def seed_sample_data(store: Store) -> None:
    """Populate store with sample catalog items and customers."""
    store.add_product(Product("P101", "Mechanical Keyboard", 12999, 10, "Electronics"))
    store.add_product(Product("P102", "Ergonomic Mouse", 4999, 15, "Electronics"))
    store.add_product(Product("P103", "USB-C Fast Cable", 1499, 25, "Accessories"))
    store.add_product(Product("P104", "Desk Pad Mat", 2499, 8, "Accessories"))
    store.add_product(Product("P105", "Limited Edition Keycap", 7999, 1, "Collectibles"))

    store.register_customer(Customer("C001", "Alice Johnson", "alice@example.com"))
    store.register_customer(Customer("C002", "Bob Smith", "bob@example.com"))


def print_header(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


class InteractiveCLI:
    """Terminal menu controller for PyShoppingCart."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.current_customer_id: str | None = "C001"
        self.active_promo_codes: list[PercentageDiscount] = []

    def run(self) -> None:
        """Main interaction loop."""
        while True:
            cust_name = "None"
            if self.current_customer_id:
                try:
                    cust_name = self.store.get_customer(self.current_customer_id).name
                except EntityNotFoundError:
                    self.current_customer_id = None

            print_header("PyShoppingCart CLI Menu")
            print(f"Active Customer: {cust_name} (ID: {self.current_customer_id})")
            print("1. Browse Catalog Products")
            print("2. View Current Shopping Cart")
            print("3. Add Item to Cart")
            print("4. Update Item Quantity in Cart")
            print("5. Remove Item from Cart")
            print("6. Apply Promo Code (Percentage Discount)")
            print("7. Checkout (Thread-Safe Order Creation)")
            print("8. View Order History & Analytics Report")
            print("9. Scan Low-Stock Products (Generator)")
            print("10. Switch or Register Customer")
            print("11. Save Store State to JSON")
            print("12. Load Store State from JSON")
            print("0. Exit")

            choice = input("\nEnter choice [0-12]: ").strip()
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                self.show_catalog()
            elif choice == "2":
                self.show_cart()
            elif choice == "3":
                self.add_item_to_cart()
            elif choice == "4":
                self.update_cart_quantity()
            elif choice == "5":
                self.remove_item_from_cart()
            elif choice == "6":
                self.apply_promo_code()
            elif choice == "7":
                self.perform_checkout()
            elif choice == "8":
                self.show_analytics()
            elif choice == "9":
                self.show_low_stock()
            elif choice == "10":
                self.manage_customer()
            elif choice == "11":
                self.save_state()
            elif choice == "12":
                self.load_state()
            else:
                print("Invalid option. Please choose between 0 and 12.")

    def show_catalog(self) -> None:
        print_header("Product Catalog")
        products = self.store.list_products()
        if not products:
            print("No products available.")
            return
        for p in products:
            print(f"[{p.id}] {p.name:<25} | {cents_to_usd(p.price_cents):>8} | Stock: {p.stock} | Cat: {p.category}")

    def show_cart(self) -> None:
        if not self.current_customer_id:
            print("Please select a customer first (Option 10).")
            return
        cart = self.store.get_or_create_cart(self.current_customer_id)
        print_header(f"Shopping Cart for {self.current_customer_id}")
        if cart.is_empty:
            print("Your cart is empty.")
            return

        for item in cart:
            print(
                f"[{item.product_id}] {item.product_name:<20} x {item.quantity:<3} @ "
                f"{cents_to_usd(item.unit_price_cents)} = {cents_to_usd(item.subtotal_cents)}"
            )

        pricing = self.store.pricing_engine.calculate_pricing(cart, self.active_promo_codes)
        print("-" * 50)
        print(f"Subtotal:       {cents_to_usd(pricing.subtotal_cents)}")
        if pricing.discount_cents > 0:
            print(f"Total Discount: -{cents_to_usd(pricing.discount_cents)}")
            for note in pricing.discount_notes:
                print(f"  * {note}")
        print(f"Payable Total:  {cents_to_usd(pricing.total_cents)}")

    def add_item_to_cart(self) -> None:
        if not self.current_customer_id:
            print("Please select a customer first (Option 10).")
            return
        prod_id = input("Enter Product ID: ").strip().upper()
        qty_str = input("Enter Quantity (default 1): ").strip()
        qty = int(qty_str) if qty_str else 1
        try:
            self.store.add_to_cart(self.current_customer_id, prod_id, qty)
            print(f"Added {qty} unit(s) of '{prod_id}' to cart.")
        except PyShoppingCartError as exc:
            print(f"Error: {exc}")

    def update_cart_quantity(self) -> None:
        if not self.current_customer_id:
            print("Please select a customer first (Option 10).")
            return
        prod_id = input("Enter Product ID to update: ").strip().upper()
        qty_str = input("Enter New Quantity (0 to remove): ").strip()
        try:
            qty = int(qty_str)
            self.store.update_cart_item(self.current_customer_id, prod_id, qty)
            print("Cart updated successfully.")
        except (ValueError, PyShoppingCartError) as exc:
            print(f"Error: {exc}")

    def remove_item_from_cart(self) -> None:
        if not self.current_customer_id:
            print("Please select a customer first (Option 10).")
            return
        prod_id = input("Enter Product ID to remove: ").strip().upper()
        try:
            self.store.remove_from_cart(self.current_customer_id, prod_id)
            print(f"Item '{prod_id}' removed from cart.")
        except PyShoppingCartError as exc:
            print(f"Error: {exc}")

    def apply_promo_code(self) -> None:
        code = input("Enter promo code (e.g. SAVE10, VIP20): ").strip().upper()
        if code in ("SAVE10", "WELCOME10"):
            promo = PercentageDiscount(code=code, percentage=10)
        elif code in ("SAVE20", "VIP20"):
            promo = PercentageDiscount(code=code, percentage=20)
        else:
            pct_str = input("Enter discount percentage for this code (1-100): ").strip()
            try:
                pct = int(pct_str)
                promo = PercentageDiscount(code=code, percentage=pct)
            except (ValueError, DomainError) as exc:
                print(f"Invalid promo: {exc}")
                return

        self.active_promo_codes.append(promo)
        print(f"Promo code '{code}' applied ({promo.percentage}% off)!")

    def perform_checkout(self) -> None:
        if not self.current_customer_id:
            print("Please select a customer first (Option 10).")
            return
        try:
            order = self.store.checkout(self.current_customer_id, extra_policies=self.active_promo_codes)
            self.active_promo_codes.clear()
            print_header("Checkout Successful!")
            print(f"Order ID:      {order.id}")
            print(f"Customer:      {order.customer_id}")
            print(f"Items:         {len(order.items)}")
            print(f"Subtotal:      {cents_to_usd(order.subtotal_cents)}")
            print(f"Discount:      -{cents_to_usd(order.discount_cents)}")
            print(f"Total Paid:    {cents_to_usd(order.total_cents)}")
            print(f"Status:        {order.status.value}")
        except PyShoppingCartError as exc:
            print(f"Checkout Failed: {exc}")

    def show_analytics(self) -> None:
        print_header("Order History & Analytics Report")
        orders = self.store.list_orders()
        summary = generate_order_summary(orders)
        print(summary)

    def show_low_stock(self) -> None:
        threshold_str = input("Enter low-stock threshold (default 5): ").strip()
        threshold = int(threshold_str) if threshold_str else 5
        print_header(f"Low Stock Scanner (Threshold <= {threshold})")
        count = 0
        for p in low_stock_scanner(self.store.list_products(), threshold=threshold):
            print(f"  * [{p.id}] {p.name} - Only {p.stock} units left!")
            count += 1
        if count == 0:
            print("All products have adequate stock levels.")

    def manage_customer(self) -> None:
        print_header("Customer Management")
        for c in self.store.list_customers():
            active_marker = " (ACTIVE)" if c.id == self.current_customer_id else ""
            print(f"[{c.id}] {c.name} <{c.email}>{active_marker}")

        action = input("\n[S]witch customer or [R]egister new customer? ").strip().upper()
        if action == "S":
            cid = input("Enter Customer ID to activate: ").strip()
            try:
                self.store.get_customer(cid)
                self.current_customer_id = cid
                print(f"Switched to customer '{cid}'.")
            except EntityNotFoundError as exc:
                print(f"Error: {exc}")
        elif action == "R":
            cid = input("New Customer ID: ").strip()
            name = input("Name: ").strip()
            email = input("Email: ").strip()
            new_cust = Customer(cid, name, email)
            self.store.register_customer(new_cust)
            self.current_customer_id = cid
            print(f"Registered and switched to {name} ({cid}).")

    def save_state(self) -> None:
        filepath = input("Enter JSON file path [store_data.json]: ").strip() or "store_data.json"
        try:
            self.store.save_state(filepath)
            print(f"Store state saved to '{filepath}'.")
        except Exception as exc:
            print(f"Save failed: {exc}")

    def load_state(self) -> None:
        filepath = input("Enter JSON file path [store_data.json]: ").strip() or "store_data.json"
        try:
            self.store.load_state(filepath)
            print(f"Store state loaded from '{filepath}'.")
        except Exception as exc:
            print(f"Load failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PyShoppingCart - CLI Store Interface")
    parser.add_argument("--data", default="store_data.json", help="Path to JSON state persistence file")
    parser.add_argument("--no-seed", action="store_true", help="Do not seed sample products and customers")
    args = parser.parse_args()

    engine = PricingEngine(
        policies=[
            BulkThresholdDiscount(threshold_cents=10000, discount_cents=1500),
        ]
    )

    store = Store(name="PyShoppingCart CLI", persistence_file=args.data, pricing_engine=engine)

    if Path(args.data).exists():
        try:
            store.load_state(args.data)
            print(f"Loaded existing store state from '{args.data}'.")
        except Exception as exc:
            print(f"Notice: Could not load existing file ({exc}). Initializing fresh.")
            if not args.no_seed:
                seed_sample_data(store)
    else:
        if not args.no_seed:
            seed_sample_data(store)

    cli = InteractiveCLI(store)
    cli.run()


if __name__ == "__main__":
    main()
