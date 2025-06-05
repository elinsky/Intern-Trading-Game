# Signal Access by Role

## Signal Overview

The game includes differentiated information access to create realistic advantages and trading opportunities. Each role receives different signals that align with their trading mandate.

## Signal Distribution Matrix

| Signal Type             | Market Maker | Hedge Fund | Arbitrage Desk | Retail | Timing          |
| ----------------------- | ------------ | ---------- | -------------- | ------ | --------------- |
| **Market Data**         | Yes          | Yes        | Yes            | Yes    | Real-time       |
| **News Headlines**      | Yes          | Yes        | Yes            | Yes    | Immediate       |
| **Volatility Forecast** | No           | Yes        | No             | No     | 1-5 ticks early |
| **Tracking Error**      | No           | No         | Yes            | No     | Real-time       |

## Public Information (All Roles)

### Market Data Feed

Everyone receives the same market data:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "instrument": "SPX_4400_CALL_2024-02-15",
  "bid": 25.40,
  "ask": 25.60,
  "last": 25.50,
  "volume": 1250,
  "book": {
    "bids": [[25.40, 100], [25.35, 200], ...],
    "asks": [[25.60, 100], [25.65, 150], ...]
  }
}
```

### News Headlines

Published to all participants simultaneously:
```json
{
  "timestamp": "2024-01-15T10:30:10Z",
  "headline": "Fed hints at tightening",
  "category": "monetary_policy"
}
```

### Probability Tables

Static reference data available to all:

- Event probabilities for regime shifts
- Historical impact statistics
- Published in game documentation

## Role-Specific Signals

### Hedge Fund: Volatility Signal

**Purpose**: Advance warning of volatility regime changes

**Content**:
```json
{
  "signal_type": "volatility_forecast",
  "current_regime": "medium",
  "forecast": {
    "next_regime": "high",
    "probability": 0.66,
    "ticks_until_change": 3
  },
  "confidence": "high"
}
```

**Characteristics**:

- Accuracy: ~66%
- Lead time: 1-5 ticks
- Updates when forecast changes
- Silent during stable regimes

**Strategic Value**:

- Position before volatility increases
- Adjust option strategies
- Size trades appropriately

### Arbitrage Desk: Tracking Error Signal

**Purpose**: Identify SPX-SPY mispricings

**Content**:
```json
{
  "signal_type": "tracking_error",
  "timestamp": "2024-01-15T10:30:00Z",
  "spx": {
    "price": 4400.00,
    "implied_spy": 440.00
  },
  "spy": {
    "price": 441.25,
    "actual": 441.25
  },
  "metrics": {
    "error_percent": 0.28,
    "error_direction": "SPY_RICH",
    "z_score": 2.1,
    "mean_reversion_ticks": 5
  }
}
```

**Characteristics**:

- Accuracy: ~80%
- Real-time updates
- Includes statistical measures
- Historical mean reversion data

**Strategic Value**:

- Immediate arbitrage opportunities
- Sizing based on z-score
- Timing exits with convergence

### Market Maker: Information Inference

**No Proprietary Signals**

## Signal Timing

### Information Release Schedule

| Time   | Event                  | Who Sees   |
| ------ | ---------------------- | ---------- |
| T-300s | Vol forecast generated | Hedge Fund |
| T-60s  | Vol signal sent        | Hedge Fund |
| T-0s   | New tick begins        | Everyone   |
| T+10s  | News published         | Everyone   |
| T+30s  | Order window opens     | Everyone   |
| T+180s | Order window closes    | Everyone   |

## Signal Reliability

### Expected Accuracy

| Signal              | Accuracy | False Positive Rate | Value Decay |
| ------------------- | -------- | ------------------- | ----------- |
| Volatility Forecast | 66%      | 34%                 | Low         |
| Tracking Error      | 80%      | 20%                 | High        |
| News Impact         | Variable | 30%                 | Medium      |

## Next Steps

- Review [Execution Rules](execution-rules.md)
