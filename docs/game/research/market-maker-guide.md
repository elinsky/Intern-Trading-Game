# Market Maker Research Guide

## Your Edge

You have the best fee structure in the game:
- **Maker rebate**: +$0.02 (double what others get)
- **Taker fee**: -$0.01 (half what others pay)
- **Requirement**: Quote ≥80% of instruments continuously

Your edge is guaranteed order flow and superior economics. The challenge is managing inventory risk while maintaining tight spreads.

## The Core Research Problem

### 1. Understanding Your Economics

Your P&L comes from three sources that interact:

- How much can you earn from pure spread capture?
- When should you pay taker fees to manage inventory?
- How does competition with another market maker affect profitability?

Key questions to investigate:
- What's the optimal spread width given competition?
- How does inventory position affect your quoting strategy?
- When is it worth missing the 80% uptime to avoid adverse selection?

### 2. Modeling Market Dynamics

You must quote without signals, inferring from order flow:

**Adverse selection:**
- Who's taking your quotes and why?
- Can you detect informed flow vs. noise?
- How do fills correlate with subsequent price moves?

**Inventory dynamics:**
- How does inventory accumulate during trends?
- What's the cost of holding losing positions?
- Optimal inventory mean reversion strategies

**Competition dynamics:**
- How tight can spreads go while remaining profitable?
- When to compete aggressively vs. back off?
- Cross-product quote coordination strategies

### 3. Making Quoting Decisions

Transform market data into profitable two-sided quotes:

**Spread determination:**
- Base spread calculation methodology
- Dynamic adjustments for volatility
- Inventory-based spread skewing
- Competition response functions

**Inventory management:**
- Position limits (±50 per option, ±200 total)
- When to skew quotes vs. hedge actively
- Cross-product inventory netting
- Emergency inventory reduction tactics

**Quote optimization:**
- Maintaining 80% uptime efficiently
- Which products to quote when selective
- Size optimization on each side
- Response time to market changes

## Measuring Success

### Primary Metrics

**Market Making Efficiency:**
```
Spread Capture Rate = Realized Spread / Quoted Spread
Quote-to-Fill Ratio = Fills / Total Quotes
Inventory Turnover = Volume / Avg Absolute Inventory
```

**Risk Management:**
```
Inventory Sharpe = Inventory P&L / Inventory Risk
Max Position Utilization = Peak Position / Position Limit
Mean Reversion Time = Average Time to Flat
```

**Competitive Performance:**
```
Market Share = Your Volume / Total Volume
Spread Leadership = Time at Best Bid/Offer
Fill Toxicity = Adverse Selection Cost per Fill
```

### Research Quality Indicators

Understand your market making mechanics:

1. **Spread Optimization**: How close to optimal are your spreads?
2. **Inventory Prediction**: Can you forecast inventory accumulation?
3. **Adverse Selection**: Toxic fill identification accuracy
4. **Uptime Efficiency**: Smart compliance with 80% requirement

## Starting Points

### Data Analysis Questions

1. **Fill Analysis**
   - Post-fill price movement patterns
   - Fill clustering and information content
   - Toxic vs. benign flow characteristics

2. **Inventory Study**
   - Accumulation patterns by market regime
   - Inventory P&L attribution
   - Optimal skew functions

3. **Spread Research**
   - Minimum viable spread by volatility
   - Competition's effect on optimal spreads
   - Cross-product spread relationships

### Simple Framework to Build On

```python
# Skeleton - expand based on your research
def calculate_quote(instrument, market_state, inventory):
    """
    instrument: option or underlying to quote
    market_state: {recent_trades, volatility, competitor_quotes}
    inventory: current position in this and related instruments

    returns: {bid_price, bid_size, ask_price, ask_size}
    """
    # Your research determines the quote logic
    pass

def manage_inventory_risk(positions, market_data):
    """
    Decide when to skew quotes vs. actively hedge
    Handle approaching position limits
    Cross-product risk management
    """
    pass

def detect_adverse_selection(recent_fills, price_moves):
    """
    Identify patterns in toxic flow
    Adjust quoting strategy based on flow analysis
    Maintain profitability despite informed traders
    """
    pass
```

## What Success Looks Like

A successful market maker will:

1. **Quote intelligently** - tight enough to capture flow, wide enough to profit
2. **Manage inventory actively** - never get stuck with large positions
3. **Adapt to competition** - find profitable equilibrium with other MM
4. **Minimize adverse selection** - avoid being picked off by informed traders
5. **Maximize rebate capture** - use fee advantage efficiently
