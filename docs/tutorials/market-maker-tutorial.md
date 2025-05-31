# Market Maker Tutorial

This tutorial guides new interns through setting up and running a market making strategy in the Intern Trading Game.

## Prerequisites

- Python 3.9 or higher
- Basic understanding of options trading concepts
- Familiarity with Jupyter notebooks

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/Intern-Trading-Game.git
cd Intern-Trading-Game
```

### 2. Install Dependencies

```bash
pip install -e .
pip install -e ".[dev]"  # For development dependencies
```

### 3. Launch the Jupyter Notebook

```bash
jupyter notebook notebooks/market_maker_starter.ipynb
```

## Market Maker Role Overview

As a market maker, your objective is to:

1. Quote fair prices for options
2. Manage inventory risk
3. Profit from the bid-ask spread
4. Maintain quotes in changing market conditions

## Basic Strategy Implementation

Here's a simple market making strategy to get you started:

```python
from intern_trading_game.exchange.order import Order

def simple_market_maker(exchange, instrument_id, spread_percentage=0.02):
    """
    A simple market making strategy that quotes around a theoretical price.

    Parameters
    ----------
    exchange : ExchangeVenue
        The exchange venue to place orders
    instrument_id : str
        The ID of the instrument to make markets for
    spread_percentage : float, default=0.02
        The percentage spread to quote (e.g., 0.02 for 2%)
    """
    # Get current market data
    market_data = exchange.get_market_summary(instrument_id)

    # Calculate theoretical price (simplified)
    theo_price = calculate_theoretical_price(instrument_id)

    # Calculate bid and ask prices
    bid_price = theo_price * (1 - spread_percentage/2)
    ask_price = theo_price * (1 + spread_percentage/2)

    # Submit orders
    bid_order = Order(
        instrument_id=instrument_id,
        side="buy",
        quantity=10,
        price=bid_price,
        trader_id="market_maker_1"
    )

    ask_order = Order(
        instrument_id=instrument_id,
        side="sell",
        quantity=10,
        price=ask_price,
        trader_id="market_maker_1"
    )

    exchange.submit_order(bid_order)
    exchange.submit_order(ask_order)

    return bid_order, ask_order
```

## Next Steps

1. Implement delta hedging to manage directional risk
2. Adjust quotes based on inventory
3. Respond to volatility regime changes
4. Optimize spread width based on market conditions

## Performance Evaluation

Your market making strategy will be evaluated on:

- P&L
- Quote width and uptime
- Risk management effectiveness
- Adaptability to changing market conditions
