# Game Parameters

## Overview

The Intern Trading Game simulation has numerous configurable parameters that control market behavior, constraints, and scoring. This document outlines the key parameters and their typical values.

## Market Structure Parameters

### Trading Configuration

| Parameter           | Default Value | Range       | Description                        |
| ------------------- | ------------- | ----------- | ---------------------------------- |
| trading_hours       | 9:30-15:00 CT | -           | Market open hours                  |
| opening_rotation    | true          | -           | Batch auction at market open       |
| continuous_matching | true          | -           | Real-time order matching           |
| latency_target      | < 5ms         | 1-50ms      | Target execution latency           |

### Instrument Configuration

| Parameter              | Default Value  | Description                |
| ---------------------- | -------------- | -------------------------- |
| underlyings            | ["SPX", "SPY"] | Available spot instruments |
| strikes_per_underlying | 5              | Number of option strikes   |
| expiration_count       | 3              | Number of expiration dates |
| expiration_range       | 1-8 weeks      | Time to expiration range   |

### Price Parameters

| Parameter         | Default Value | Description             |
| ----------------- | ------------- | ----------------------- |
| spx_initial_price | 4400          | Starting SPX price      |
| spy_ratio         | 10            | SPX/SPY price ratio     |
| min_tick_size     | 0.01          | Minimum price increment |
| max_tick_move     | 5%            | Circuit breaker limit   |

## Volatility Regime Parameters

### Regime Definitions

| Regime | Annual Vol | Per-Second Std | Persistence     |
| ------ | ---------- | -------------- | --------------- |
| Low    | 10%        | 0.0016%        | 30 min - 2 hrs  |
| Medium | 20%        | 0.0032%        | 20 min - 1 hr   |
| High   | 50%        | 0.0080%        | 10 min - 30 min |

### Transition Matrix

```
         To Low  To Med  To High
From Low   0.95    0.04    0.01
From Med   0.02    0.94    0.04
From High  0.01    0.09    0.90
```

## Role-Specific Parameters

### Market Maker

| Parameter                | Value  | Description            |
| ------------------------ | ------ | ---------------------- |
| quote_uptime_requirement | 80%    | Minimum quote presence |
| maker_rebate             | +$0.02 | Per contract rebate    |
| taker_fee                | -$0.01 | Per contract fee       |
| position_limit           | ±50    | Per option limit       |
| total_position_limit     | ±200   | Portfolio limit        |
| max_spread_width         | 10%    | Maximum quote spread   |

### Hedge Fund

| Parameter            | Value     | Description                |
| -------------------- | --------- | -------------------------- |
| maker_rebate         | +$0.01    | Per contract rebate        |
| taker_fee            | -$0.02    | Per contract fee           |
| position_limit       | 150       | Per option limit           |
| total_position_limit | 500       | Portfolio limit            |
| signal_accuracy      | 66%       | Volatility signal accuracy |
| signal_lead_time     | 1-5 ticks | Advance warning            |

### Arbitrage Desk

| Parameter            | Value  | Description             |
| -------------------- | ------ | ----------------------- |
| maker_rebate         | +$0.01 | Per contract rebate     |
| taker_fee            | -$0.02 | Per contract fee        |
| position_limit       | 100    | Per option limit        |
| total_position_limit | 300    | Portfolio limit         |
| signal_accuracy      | 80%    | Tracking error accuracy |
| target_ratio         | 10:1   | SPX:SPY value ratio     |

### Retail Flow Simulation

| Parameter         | Value            | Description             |
| ----------------- | ---------------- | ----------------------- |
| orders_per_tick   | Poisson(λ=3)     | Random order generation |
| order_size        | Exponential(μ=5) | Size distribution       |
| max_position      | 50               | Total position limit    |
| call_probability  | 60%              | Bullish bias            |
| otm_preference    | 70%              | Prefer cheap options    |
| market_order_rate | 40%              | Takes liquidity         |

### Retail Behavioral Patterns

| Pattern          | Probability | Trigger      | Effect        |
| ---------------- | ----------- | ------------ | ------------- |
| Momentum Chasing | 30%         | 3-tick trend | 2x size       |
| Panic Selling    | 20%         | 5% drawdown  | 3x size sells |
| FOMO Buying      | 25%         | Vol spike    | Buy OTM calls |
| Profit Taking    | 15%         | 20% gain     | Sell 50%      |

## Signal Parameters

### News Event Configuration

| Parameter             | Default   | Description               |
| --------------------- | --------- | ------------------------- |
| event_frequency       | 1-4 hours | Poisson distribution      |
| regime_shift_events   | 40%       | Percentage causing shifts |
| price_jump_events     | 30%       | Percentage causing jumps  |
| false_positive_events | 30%       | No effect events          |

### Tracking Error Parameters

| Parameter            | Default    | Description           |
| -------------------- | ---------- | --------------------- |
| base_correlation     | 0.98       | SPX-SPY correlation   |
| tracking_error_std   | 0.15%      | Daily tracking error  |
| mean_reversion_speed | 5-10 ticks | Convergence half-life |
| signal_threshold     | 0.15%      | Minimum to signal     |

## Order Management Parameters

### Order Limits

| Role         | Orders/Tick | Min Size | Max Size |
| ------------ | ----------- | -------- | -------- |
| Market Maker | 100         | 1        | 1000     |
| Hedge Fund   | 50          | 1        | 500      |
| Arbitrage    | 75          | 1        | 500      |
| Retail Flow  | Poisson(3)  | 1        | 50       |

### Execution Parameters

| Parameter          | Value       | Description             |
| ------------------ | ----------- | ----------------------- |
| matching_algorithm | Price-Time  | Order priority          |
| partial_fills      | Enabled     | Allow partial execution |
| order_expiration   | End of tick | All orders expire       |
| self_trade         | Allowed     | Can trade with yourself |

### Phase Transition Parameters

| Parameter             | Default Value | Description                                                          |
| --------------------- | ------------- | -------------------------------------------------------------------- |
| phase_check_interval  | 0.1 seconds   | Maximum delay before checking for market phase transitions           |
| order_queue_timeout   | 0.01 seconds  | Maximum wait time for new orders before checking market phases      |

These parameters control the responsiveness of automatic market operations:

- **phase_check_interval**: How often the system checks for phase changes (e.g., market open/close)
- **order_queue_timeout**: How long to wait for orders during quiet periods before checking phases

Lower values increase responsiveness but consume more CPU. Higher values reduce overhead but may delay critical operations like opening auctions.

## Scoring Parameters

### Weight Distribution

| Component                | Weight | Description              |
| ------------------------ | ------ | ------------------------ |
| Quantitative Performance | 70%    | P&L, risk metrics        |
| Qualitative Factors      | 30%    | Code, research, teamwork |

### Penalty Thresholds

| Violation              | Threshold   | Penalty             |
| ---------------------- | ----------- | ------------------- |
| Minor Position Breach  | <10% over   | -5% score           |
| Major Position Breach  | 10-25% over | -15% score          |
| Severe Position Breach | >25% over   | -30% score          |
| Quote Uptime Failure   | <80%        | Graduated penalties |

## Adjustable Parameters

### Dynamic Adjustments

Some parameters may be adjusted during the game:

- Volatility regime probabilities
- Event frequencies
- Signal accuracies
- Fee structures

### Fixed Parameters

These remain constant throughout:

- Position limits
- Role constraints
- Tick duration
- Scoring weights

## Configuration File Format

See [Example Configuration](example-config.yaml) for a complete configuration file showing all parameters and their relationships.
