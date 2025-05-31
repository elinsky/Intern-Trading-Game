# Testing Rule – “Feature Commits must ship Unit Tests”

## Purpose
Every new feature must be verifiable by automated tests that clearly specify the intended behaviour.
Unit‑level coverage with the **Given‑When‑Then** pattern ensures each change is easy to understand, safe to refactor, and resistant to regressions.

---

## When does this rule apply?
A commit (or MR/PR) is treated as a **Feature Commit** under the same criteria defined in `02-documentation.md`:

- The commit message starts with `feat:` or `feature:`
- A new file is added under `/src`
- An existing source file’s public interface changes

---

## Required testing artifacts
For every Feature Commit:

1. **At least one new or updated test file** must be present in `/tests/`.
2. Each new test **must follow the Given‑When‑Then structure**, expressed in **one** of these ways:
   • Using a BDD framework (for example, `pytest-bdd`, `behave`, `cucumber`), with `Given`, `When`, `Then` keywords in the scenario text.
   • Or, in plain `pytest` tests:
     – Place `# Given`, `# When`, and `# Then` comments (or docstring sections) delimiting the three phases.
     – Each section must include detailed business context comments that explain the market conditions, trading actions, and expected outcomes from a business perspective.
     – Within each block, keep the code minimal and side‑effect free except in the **When** phase.

### File naming and location

    Intern-Trading-Game/
    ├── src/
    │   └── intern_trading_game/       # production code
    │       ├── exchange/              # exchange components
    │       └── instruments/           # financial instruments
    └── tests/
        ├── test_exchange.py           # exchange tests
        ├── test_main.py               # main module tests
        └── test_<feature>.py          # other feature tests

- Test modules must start with `test_`.
- Each scenario function must start with `test_` and contain **one and only one** Given‑When‑Then sequence.

### Example: pytest with comments

    # tests/test_exchange.py

    def test_order_matching():
        # Given - Market setup with a resting buy order
        # We have an exchange venue with a test instrument listed for trading.
        # A trader (trader1) has placed a buy order for 10 contracts at $5.25,
        # which is sitting in the order book as a resting order waiting to be matched.
        exchange = ExchangeVenue()
        instrument = Instrument(symbol="TEST", underlying="TEST")
        exchange.list_instrument(instrument)
        buy_order = Order(instrument_id="TEST", side="buy", quantity=10, price=5.25, trader_id="trader1")
        exchange.submit_order(buy_order)

        # When - A matching sell order arrives in the market
        # A second trader (trader2) submits a sell order for 5 contracts at the same price ($5.25),
        # which should trigger the matching engine to execute a trade between the two orders.
        sell_order = Order(instrument_id="TEST", side="sell", quantity=5, price=5.25, trader_id="trader2")
        result = exchange.submit_order(sell_order)

        # Then - Order matching creates a trade with correct details
        # The sell order should be completely filled since its quantity (5) is less than
        # the resting buy order's quantity (10).
        # A trade should be created at the price of $5.25 for 5 contracts.
        # The buy order should remain in the book with 5 contracts remaining.
        assert result.status == "filled"
        assert len(result.fills) == 1
        assert result.fills[0].price == 5.25
        assert result.fills[0].quantity == 5

---

## Enforcement checklist (evaluated by Cline)
1. Detect Feature Commit.
2. Verify tests:
   • At least one file added or changed under `/tests/`.
   • Each new or modified test file contains the tokens `Given`, `When`, and `Then` (case‑insensitive) in comments, docstrings, or BDD scenario text.
   • Each of these sections must include descriptive comments that explain the business context, not just code.
3. Fail the commit with guidance if criteria are unmet.
4. Allow override only when the commit footer contains:

       #tests-override: true

   Overrides should be rare and justified (for example, prototype spike).

---

## Author‑facing snippet
Generate a skeleton test with:

    cline /snippet new-test

The snippet inserts:

    def test_<feature>():
        # Given - [Describe the initial market state and preconditions]
        # Provide a complete business context explaining what market conditions
        # and initial setup are required for this test.


        # When - [Describe the trading action or event being tested]
        # Explain what market event or trader action is occurring and why
        # this is the specific behavior we want to test.


        # Then - [Describe the expected market outcome and business implications]
        # Detail what should happen from a trading perspective, including
        # order states, trade execution details, and any market data changes.

---

## Continuous integration integration
- Pre‑commit hook **tests-lint** runs `pytest --collect-only` to ensure new tests import correctly.
- CI job **tests-enforce** executes `/scripts/ci/enforce_tests.sh`, implementing the checklist above.
  The script exits status 1 on violation.

---

## Living rule
Update this rule whenever testing conventions or directory layouts change.
