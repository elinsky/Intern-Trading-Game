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
    base_buy_probability: 0.50
    momentum_factor: 0.2  # Increase buy prob in uptrends
    contrarian_factor: 0.1  # Some retail fades moves
    
  # Dynamic adjustment
  if price_up_last_3_ticks:
    buy_probability = base + momentum_factor
  elif price_down_last_3_ticks:
    buy_probability = base - momentum_factor + contrarian_factor
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

### Behavioral Patterns

**Trading Patterns**
```yaml
  behavioral_patterns:
    chase_momentum:
      probability: 0.30
      trigger: "3_tick_trend"
      size_multiplier: 2.0
    
    panic_selling:
      probability: 0.20
      trigger: "5%_drawdown"
      sell_everything: false
      size_multiplier: 3.0
    
    fomo_buying:
      probability: 0.25
      trigger: "volatility_spike"
      target: "otm_calls"
    
    profit_taking:
      probability: 0.15
      trigger: "20%_gain"
      sell_percent: 0.50
```

## Order Flow Characteristics

### Time-of-Day Patterns
```yaml
  activity_patterns:
    morning_spike:
      hours: [9, 10]
      activity_multiplier: 1.5
    
    lunch_lull:
      hours: [12, 13]
      activity_multiplier: 0.7
    
    close_rush:
      hours: [15, 16]
      activity_multiplier: 2.0
```

### Market Condition Response
```yaml
  market_response:
    high_volatility:
      order_frequency: "+50%"
      size_reduction: "-30%"
      otm_preference: "+20%"
    
    trending_market:
      momentum_following: "+40%"
      contrarian: "+10%"
    
    range_bound:
      activity: "-20%"
      strike_concentration: "+30%"
```

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

### Bullish Retail Environment
```yaml
retail_bullish:
  call_probability: 0.75
  buy_probability: 0.65
  otm_call_preference: 0.85
  size_on_dips: 2.0
```

### Fearful Retail Environment
```yaml
retail_fearful:
  put_probability: 0.70
  sell_probability: 0.60
  market_order_percent: 0.60
  panic_threshold: "3%"
```

### Balanced Random Walk
```yaml
retail_random:
  call_probability: 0.50
  buy_probability: 0.50
  random_walk: true
  no_patterns: true
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

## Advanced Configuration

### Multi-Agent Approach
```yaml
retail_agents:
  - type: "momentum_chaser"
    weight: 0.30
    config: {...}
  
  - type: "contrarian"
    weight: 0.20
    config: {...}
  
  - type: "random"
    weight: 0.50
    config: {...}
```

### Adaptive Behavior
```yaml
adaptive_retail:
  learn_from_pnl: true
  adaptation_rate: 0.01
  memory_ticks: 100
  max_behavior_shift: 0.20
```

## Fee Structure

Retail flow faces standard fees:
- **Maker Fee**: -$0.01
- **Taker Fee**: -$0.03
- Predominantly takes liquidity due to market order usage

## Summary

The retail flow simulation creates a realistic, configurable source of market activity that enhances the trading environment. By carefully tuning parameters, the simulation generates order flow that exhibits common retail characteristics: momentum chasing, panic selling, preference for cheap out-of-money options, and general market noise. This makes the game more challenging and realistic for all participants.