# Retail Flow Simulation

## Overview

The Retail Flow represents automated, random trading activity that simulates typical retail investor behavior. This configurable system generates realistic market noise, liquidity, and trading patterns without human participation.

## Purpose

Retail flow simulation serves critical market functions:
- Creates realistic order flow patterns
- Adds liquidity at various price levels
- Generates market noise and unpredictability
- Simulates behavioral biases common in retail trading
- Makes the market more challenging and realistic

## Configuration Parameters

### Order Generation

**Frequency Distribution**
```yaml
retail:
  orders_per_tick:
    distribution: "poisson"
    mean: 3
    max: 10

  inter_arrival_time:
    distribution: "exponential"
    lambda: 0.5  # Average 2 orders per minute within tick
```

**Order Size Distribution**
```yaml
  order_size:
    distribution: "exponential"
    mean: 5
    min: 1
    max: 50
    round_to: 5  # Round to nearest 5 lots
```

### Directional Bias

**Buy/Sell Ratio**
```yaml
  directional_bias:
    base_buy_probability: 0.50  # Equal buy/sell probability
```

### Product Selection Bias

**Put/Call Skew**
```yaml
  product_selection:
    call_probability: 0.60  # Retail typically bullish
    otm_preference: 0.70   # Prefer out-of-money
    weekly_preference: 0.80 # Prefer near-term expiry

  strike_selection:
    distribution: "normal"
    mean: "current_price"
    stdev_percent: 2.0  # How far OTM to go
    skew_factor: 1.5    # Prefer OTM calls
```


## Order Flow Characteristics


## Implementation Details

### Order Type Mix
```yaml
  order_types:
    market_orders: 0.40  # Retail uses more market orders
    limit_orders: 0.60

  limit_order_pricing:
    aggressive: 0.30  # At or through market
    passive: 0.50     # Behind market
    far: 0.20         # Far from market
```

### Position Management
```yaml
  position_behavior:
    max_position: 50
    close_probability: 0.05  # Per tick
    hold_duration:
      distribution: "exponential"
      mean_ticks: 20
    stop_loss: null  # Retail rarely uses stops
```

## Statistical Properties

### Expected Characteristics

**Volume Distribution**
- Daily volume: 100-500 contracts
- Peak hours: 2-3x average
- Quiet periods: 0.5x average

**Price Impact**
- Individual orders: Minimal
- Cumulative effect: Can move markets in trends
- Correlation with volatility: Positive

**Behavioral Biases**
- Disposition effect: Hold losers, sell winners
- Herding: Increase activity after big moves
- Overconfidence: Larger sizes after wins

## Configuration Examples

### Basic Configuration
```yaml
retail:
  orders_per_tick:
    distribution: "poisson"
    mean: 3
  order_size:
    distribution: "exponential"
    mean: 5
  call_probability: 0.60  # Slight bullish bias
  buy_probability: 0.50   # Balanced buy/sell
  market_order_percent: 0.40  # Mix of order types
```

## Monitoring and Metrics

### Key Metrics Tracked
- Orders per tick (mean, std dev)
- Size distribution
- Product mix (calls vs puts)
- Directional bias over time
- P&L (for realism check)

### Calibration Goals
- Realistic volume: 5-15% of total
- No systematic profit/loss
- Natural-looking flow
- Appropriate randomness

## Impact on Market

### For Market Makers
- Additional flow to capture
- More noise in signals
- Opportunities in retail overreaction

### For Hedge Funds
- Momentum amplification
- Contrarian opportunities
- Noise to filter out

### For Arbitrage Desks
- Minimal direct impact
- Can create temporary dislocations
- Additional volume for hiding trades


## Fee Structure

Retail flow faces standard fees:
- **Maker Fee**: -$0.01
- **Taker Fee**: -$0.03
- Predominantly takes liquidity due to market order usage

## Summary

The retail flow simulation creates a realistic, configurable source of market activity that enhances the trading environment. By carefully tuning parameters, the simulation generates order flow that exhibits common retail characteristics: momentum chasing, panic selling, preference for cheap out-of-money options, and general market noise. This makes the game more challenging and realistic for all participants.
