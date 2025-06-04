# Implementation Guide

## 1. Feed Publishing Requirements

- **Underlying Prices**:
  - SPX and SPY spot values published every tick.

- **Option Parameters**:
  - Strike list and expirations for each underlying. (Static unless updated.)

- **News Events**:
  - Headlines with known triggering probabilities.

- **Snapshot Data** (end of tick):
  - Order book state (bids/asks, sizes).
  - All fills and executions.
  - Position and P&L per desk.

- **Signals (Role-Specific)**:
  - **Hedge Fund**: Receives advance warning before news events with:
    - Volatility regime change prediction (true/false)
    - Probability transition matrix (3x3 for low/medium/high vol states)
    - Signal arrives configurable ticks before the news event
    - Signal accuracy is configurable (e.g., 66%)
  - **Arbitrage Desk**: “SPX–SPY tracking error” instantly.

---

## 2. Signal Injection Process

1. **Generate News Event**:
   - Randomly sample from the fixed probability table.
   - Publish headline immediately.

2. **Compute True Regime Shift** (internally):
   - If the event triggers a shift, flip to new vol state.

3. **Publish Advance Signals**:
   - Before news events (configurable timing), send Hedge Fund:
     - Prediction of whether event will trigger regime change
     - Full probability transition matrix for next state
   - Instantly calculate and publish "tracking error" for Arb Desk.
---

## 3. P&L Calibration & Balancing

- **Why Balance**: Ensure no single role has an unsustainable advantage.
- **Methods**:
  1. **Signal Accuracy**: HF signal at 66% accuracy, Arb signal at 80% accuracy; add noise/false positives.
  2. **Fee Structures**:
     - **Market Makers**: Enhanced maker rebates (+\$0.02) and reduced taker fees (–\$0.01).
     - **Hedge Fund**: Standard fees (+\$0.01 maker / –\$0.02 taker) with position limits (150 per option).
     - **Arbitrage Desk**: Standard fees (+\$0.01 maker / –\$0.02 taker) with scoring bonus for round-trips.
  3. **Position Limits**:
     - HF: Maximum 150 contracts per option, 500 total across all options.
     - MM: Maximum ±50 net contracts per product (SPX/SPY).
     - Arb: Maximum 100 contracts per leg, must maintain paired trades (2:1 ratio).

---

## 4. Configurable Parameters (Backend Example)

- **underlying_dynamics**:
  - **vol_regime_model**:
    - states: ["low", "medium", "high"]
    - volatilities: [0.1, 0.2, 0.5]
    - transition_probabilities: 3x3 matrix
    - mean_durations: {"low": 50, "medium": 40, "high": 30}
- **iv_realized_spread**: Constant gap between IV and realized vol.
- **spy_spx_tracking_noise**: Mean/standard deviation for SPY’s tracking error.
- **role_signals**:
  - **hedge_fund_signal**:
    - advance_warning_ticks: 2 (how many ticks before news event)
    - accuracy: 0.66 (66% correct predictions)
    - includes_transition_matrix: true
  - **arbitrage_signal**:
    - accuracy: 0.80
- **retail_flow_bias**:
  - aggression: fraction of retail orders that cross the spread.
  - volume_per_tick: number of retail orders per tick.
(Refer to `config/example-game-config.yaml` for sample format.)

---

## 5. How to Enable Research

- **Hidden but Discoverable Structure**:
  - Do not expose config directly; let interns infer patterns through data analysis.
- **Encourage Pattern Recognition**:
  - Volatility clustering, event-driven jumps, correlation breakdowns.
- **Reward Insight**:
  - Extra points for teams that document and exploit hidden fundamentals effectively.

---
