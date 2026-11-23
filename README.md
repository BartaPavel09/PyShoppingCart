# PyShoppingCart

A clean, thread-safe shopping cart and inventory management engine written in Python 3.11+.

`PyShoppingCart` models an e-commerce store with catalog inventory, customer management, active shopping carts, discount rules, immutable order creation, and thread-synchronized checkout.

---

## Features

- **Strict Integer Cents Currency:** All monetary amounts (`price_cents`, `subtotal_cents`, `discount_cents`, `total_cents`) are strictly stored and computed as integer cents (e.g. `$19.99` = `1999`). Zero floating-point arithmetic to prevent rounding and IEEE-754 precision issues.
- **Cart vs. Order Separation:** Carts represent temporary, mutable shopping sessions. Upon checkout, inventory is deducted, a confirmed, immutable `Order` snapshot is created, and the cart is reset.
- **Discount Engine:** Modular discount policies (`PercentageDiscount`, `BulkThresholdDiscount`) with sequential stacking rules and a hard floor at 0 cents so totals never become negative.
- **JSON Persistence:** Custom `JSONEncoder` and `object_hook` deserialization for saving and loading the complete store state (products, customers, carts, orders) to/from JSON.
- **Generators & Iterators:** Memory-efficient lazy generator (`low_stock_scanner`) and custom iterator class (`OrderBatchIterator`) for chunked order processing.
- **Operation Decorators:** Execution timing (`@timed_operation`) and state logging (`@log_state_transition`) built with `functools.wraps`.
- **Pure Functional Reporting:** Side-effect-free order analytics pipeline using `filter`, `map`, and `reduce`.
- **Thread Safety:** Shared inventory checkout is protected using `threading.Lock`, guaranteeing zero overselling under high concurrent load.

---

## Architecture & Design

### 1. Domain Models (`src/pyshoppingcart/models/`)
- **`Product`**: Encapsulates item catalog data, price in integer cents, current stock, and stock mutation methods (`deduct_stock`, `restock`). Invariants enforce positive prices and non-negative stock.
- **`Customer`**: Represents a registered customer with unique ID, name, and email.
- **`Cart` & `CartItem`**: Tracks active selections. Validates requested quantities against available stock without reserving inventory prematurely. Implements `__iter__` for item iteration.
- **`Order` & `OrderItem`**: Immutable snapshot created upon successful checkout, capturing frozen product names, unit prices, applied discounts, and timestamp.

### 2. Pricing & Discounts (`src/pyshoppingcart/pricing/`)
- `DiscountPolicy`: Abstract base class for promotional strategies.
- `BulkThresholdDiscount`: Fixed cent deduction if the cart subtotal meets or exceeds a spending threshold (e.g., $15.00 off orders over $100.00).
- `PercentageDiscount`: Percentage reduction applied to the remaining balance (e.g., 10% promo code).
- **Stacking Rule:**
  1. Threshold discounts apply first against the gross subtotal.
  2. Percentage discounts apply subsequently to the remaining balance.
  3. The final total is clamped at `max(0, balance)` so discounts can never cause a negative balance.

### 3. Concurrency & Synchronization (`src/pyshoppingcart/store.py`)
In a multi-user store, checkout operations compete for the same inventory. `Store.checkout` synchronizes stock deduction using a shared `threading.Lock`:
- The lock guards the critical section: reading stock, validating availability, and decrementing quantity.
- **Acceptance Scenario:** If multiple concurrent worker threads attempt to buy the last remaining unit of a product (`stock = 1`), exactly **one** thread succeeds. All other threads receive an `InsufficientStockError`, and the inventory stock remains strictly non-negative (`stock == 0`).

### 4. Functional Analytics & Rationale (`src/pyshoppingcart/reporting/`)
The order summary report (`generate_order_summary`) is implemented as a **pure function** using `filter()`, `map()`, and `reduce()`/`sum`:

#### Why a Functional Pipeline over an Imperative Loop?
1. **Declarative Clarity:** Expresses *what* transformations are needed (filter matching orders $\rightarrow$ map to revenues $\rightarrow$ reduce to total) rather than managing low-level loop counters and mutable accumulator variables.
2. **Purity & No Side Effects:** The function does not modify input collections or global state. Given the same inputs, it deterministically returns the same result.
3. **Thread Safety & Immutability:** Because no shared state is mutated during execution, multiple threads can safely generate reports concurrently without locks.
4. **Composability:** Filtering predicates and mapping functions can be easily isolated, tested, and composed.

---

## Project Structure

```
PyShoppingCart/
├── pyproject.toml              # Build config and pytest options
├── README.md                   # Documentation and usage guide
├── demo.py                     # Standalone demonstration script
├── src/
│   └── pyshoppingcart/
│       ├── __init__.py         # Public exports
│       ├── exceptions.py       # Domain exception hierarchy
│       ├── store.py            # Central Store aggregate with threading.Lock
│       ├── cli.py              # Interactive terminal CLI
│       ├── models/             # Domain entities (Product, Cart, Order, Customer)
│       ├── pricing/            # Discount policies and PricingEngine
│       ├── persistence/        # JSON repository, custom encoder, and object hook
│       ├── reporting/          # Analytics pipeline, low-stock generator, batch iterator
│       └── utils/              # Timing and logging decorators, currency formatters
└── tests/                      # Automated test suite (49 tests)
    ├── test_models.py          # Domain model invariants and validation
    ├── test_pricing.py         # Discount calculation and stacking
    ├── test_persistence.py      # JSON serialization roundtrips
    ├── test_reporting.py        # Generators, iterators, and functional report
    ├── test_decorators.py       # Timing and logging decorators
    └── test_concurrency.py      # Multi-threaded race condition tests
```

---

## Installation & Setup

Requires Python 3.11+.

```bash
# 1. Clone repository
git clone https://github.com/BartaPavel09/PyShoppingCart.git
cd PyShoppingCart

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies and package in editable mode
pip install pytest
pip install -e .
```

---

## Usage

### Run the Scripted Demo
The demo runs through all operations non-interactively (catalog setup, cart operations, stock rejection, discount stacking, atomic checkout, JSON save/reload, generator scanning, functional report, and a 5-thread concurrency race):

```bash
python demo.py
```

### Run the Interactive CLI
```bash
python -m pyshoppingcart.cli
```

CLI options:
- `--data <path>`: Custom JSON file for state persistence (default: `store_data.json`).
- `--no-seed`: Start with an empty store instead of sample products.

### Run the Test Suite
```bash
pytest -v
```

All 49 unit and concurrency tests execute in under 0.1s.
