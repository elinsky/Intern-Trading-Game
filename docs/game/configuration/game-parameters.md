# Game Parameters

## Overview

The Intern Trading Game simulation has numerous configurable parameters that control market behavior, constraints, and scoring. This document outlines the key parameters and their typical values.

## Market Structure Parameters

### Tick Configuration
| Parameter | Default Value | Range | Description |
|-----------|---------------|-------|-------------|
| tick_duration | 5 minutes | 1-60 min | Time between market updates |
| order_window | 3 minutes | 1-4 min | Time to submit orders each tick |
| batch_processing | true | - | Orders processed simultaneously |

### Instrument Configuration
| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| underlyings | ["SPX", "SPY"] | Available spot instruments |
| strikes_per_underlying | ~15 | Covers ±30% moves, all deltas |
| expiration_count | 4-6 | Weekly expirations only |
| expiration_cycle | Weekly | Every week |
| trading_days | Tue, Thu | Two days per week |
| trading_hours | 9:30 AM - 3:00 PM CT | 5.5 hours per day |

### Price Parameters
| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| spx_initial_price | 4400 | Starting SPX price |
| spy_ratio | 10 | SPX/SPY price ratio |
| min_tick_size | 0.01 | Minimum price increment |
| max_tick_move | 5% | Circuit breaker limit |

## Volatility Regime Parameters

### Regime Definitions
| Regime | Annual Vol | 5-min Std Dev | Persistence |
|--------|------------|---------------|-------------|
| Low | 10% | 0.04% | 50-200 ticks |
| Medium | 20% | 0.09% | 30-100 ticks |
| High | 50% | 0.22% | 10-50 ticks |

### Transition Matrix
```
         To Low  To Med  To High
From Low   0.95    0.04    0.01
From Med   0.02    0.94    0.04
From High  0.01    0.09    0.90
```

## Role-Specific Parameters

### Market Maker
| Parameter | Value | Description |
|-----------|-------|-------------|
| quote_uptime_requirement | 80% | Minimum quote presence |
| maker_rebate | +$0.02 | Per contract rebate |
| taker_fee | -$0.01 | Per contract fee |
| position_limit | ±50 | Per option limit |
| total_position_limit | ±200 | Portfolio limit |
| max_spread_width | 10% | Maximum quote spread |

### Hedge Fund
| Parameter | Value | Description |
|-----------|-------|-------------|
| maker_rebate | +$0.01 | Per contract rebate |
| taker_fee | -$0.02 | Per contract fee |
| position_limit | 150 | Per option limit |
| total_position_limit | 500 | Portfolio limit |
| signal_accuracy | 66% | Volatility signal accuracy |
| signal_lead_time | 1-5 ticks | Advance warning |

### Arbitrage Desk
| Parameter | Value | Description |
|-----------|-------|-------------|
| maker_rebate | +$0.01 | Per contract rebate |
| taker_fee | -$0.02 | Per contract fee |
| position_limit | 100 | Per option limit |
| total_position_limit | 300 | Portfolio limit |
| signal_accuracy | 80% | Tracking error accuracy |
| target_ratio | 10:1 | SPX:SPY value ratio |

### Retail Flow Simulation
| Parameter | Value | Description |
|-----------|-------|-------------|
| orders_per_tick | Poisson(λ=3) | Random order generation |
| order_size | Exponential(μ=5) | Size distribution |
| max_position | 50 | Total position limit |
| call_probability | 60% | Bullish bias |
| otm_preference | 70% | Prefer cheap options |
| market_order_rate | 40% | Takes liquidity |


## Signal Parameters

### News Event Configuration
| Parameter | Default | Description |
|-----------|---------|-------------|
| event_frequency | 1-4 hours | Poisson distribution |
| regime_shift_events | 40% | Percentage causing shifts |
| price_jump_events | 30% | Percentage causing jumps |
| false_positive_events | 30% | No effect events |

### Tracking Error Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| base_correlation | 0.98 | SPX-SPY correlation |
| tracking_error_std | 0.15% | Daily tracking error |
| mean_reversion_speed | 5-10 ticks | Convergence half-life |
| signal_threshold | 0.15% | Minimum to signal |

## Order Management Parameters

### Order Limits
| Role | Orders/Tick | Min Size | Max Size |
|------|-------------|----------|----------|
| Market Maker | 100 | 1 | 1000 |
| Hedge Fund | 50 | 1 | 500 |
| Arbitrage | 75 | 1 | 500 |
| Retail Flow | Poisson(3) | 1 | 50 |

### Execution Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| matching_algorithm | Price-Time | Order priority |
| partial_fills | Enabled | Allow partial execution |
| order_expiration | End of tick | All orders expire |
| self_trade | Allowed | Can trade with yourself |

## Scoring Parameters

### Weight Distribution
| Component | Weight | Description |
|-----------|--------|-------------|
| Quantitative Performance | 70% | P&L, risk metrics |
| Qualitative Factors | 30% | Code, research, teamwork |

### Penalty Thresholds
| Violation | Threshold | Penalty |
|-----------|-----------|---------|
| Minor Position Breach | <10% over | -5% score |
| Major Position Breach | 10-25% over | -15% score |
| Severe Position Breach | >25% over | -30% score |
| Quote Uptime Failure | <80% | Graduated penalties |

## System Parameters

### Technical Limits
| Parameter | Value | Description |
|-----------|-------|-------------|
| api_rate_limit | 100 req/sec | Per team limit |
| connection_timeout | 30 seconds | Reconnection window |
| max_message_size | 1 MB | Order batch limit |
| latency_target | <100ms | System response time |

### Data Retention
| Parameter | Value | Description |
|-----------|-------|-------------|
| tick_history | Full game | All ticks stored |
| order_history | Full game | All orders logged |
| position_snapshots | Every tick | Complete state |
| performance_metrics | Real-time | Continuous calculation |

## Environmental Parameters

### Game Phases
| Phase | Duration | Parameters |
|-------|----------|------------|
| Learning | Week 1-2 | Reduced volatility, practice mode |
| Competition | Week 3-6 | Full parameters active |
| Final | Week 7-8 | Possible increased volatility |

### Special Events
| Event Type | Frequency | Effect |
|------------|-----------|--------|
| Volatility Storm | 1-2 per game | Extended high volatility |
| Flash Event | 2-3 per game | Sudden price jumps |
| Quiet Period | Daily | Reduced activity windows |

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

## Using Parameters in Strategy

### Parameter Awareness
Your bot should:
1. Read configuration at startup
2. Adapt to parameter values
3. Not hard-code assumptions
4. Handle parameter changes

### Example Usage
```python
# Read configuration
config = load_game_config()

# Adapt strategy
if config.volatility_regime == "high":
    widen_spreads(factor=2.0)
    reduce_position_size(factor=0.5)

# Respect limits
max_position = config.role_limits.position_limit
current_position = get_current_position()
available_capacity = max_position - abs(current_position)
```

## Configuration File Format

See [Example Configuration](example-config.yaml) for a complete configuration file showing all parameters and their relationships.
