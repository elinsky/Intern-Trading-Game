# Role: Hedge Fund

## One-Line Mission
Detect mispriced implied volatility and use directional or volatility trades to capitalize on regime shifts.

---

## 1. Role Details
- **Product Access**: SPX and SPY options and underlyings.
- **Delta Hedging**: Allowed; can trade underlying futures/spot to remain neutral.
- **Signal Access**: 
  - Receives advance warning a configurable number of ticks before news events
  - Signal includes:
    - **Regime Change Prediction**: Whether the news event will trigger a volatility regime change
    - **Probability Transition Matrix**: Shows transition probabilities from current state to next state
    - **Three Volatility States**: Low vol, medium vol, and high vol (all configurable)
    - **Signal Accuracy**: Configurable (e.g., 66% accuracy means signal is correct 66% of the time)
  - Signal timing is configurable (e.g., arrives 2 ticks before the actual news event)
- **Trading Frequency**: Can trade every tick during the submission window.
- **Fees/Incentives**:
  - **Standard Maker Rebate**: +\$0.01 per filled side (on single-sided limit orders).
  - **Standard Taker Fee**: -\$0.02 per executed contract.
  - **Position Limits**: Maximum 150 contracts per option, 500 total across all options.
  - **Fee Structure**: Standard fees (no enhanced rebates like Market Makers).
- **Constraints**:
  - **No Market Making**: Cannot quote two-sided markets (no simultaneous bid and ask).
  - Can only place single-sided limit orders or market orders.
  - Position limits: 150 per option, 500 total options, 200 underlying contracts.
  - Must use directional or volatility strategies without market making capabilities.
- **Scoring Focus**:
  - P&L from realized vs. implied volatility trades.
  - Risk-adjusted returns.
  - Strategy adaptiveness (reaction to regime changes).
  - Research output (back-testing quality).

---

## 2. Advantages
- **Execution Flexibility**: Can use limit orders for better fills or market orders for immediacy.
- **Signal Edge**: Gets advance warning before news events with:
  - Regime change predictions
  - Full probability transition matrix between volatility states
  - Configurable lead time to position before the market reacts
- **No Quoting Obligation**: Unlike Market Makers, free to trade opportunistically without coverage requirements.
- **Strategy Flexibility**: Can run directional bets, volatility trades (straddles/strangles), or cross-product spreads (using single-sided orders).
- **Alpha Potential**: High upside if signal accuracy is leveraged correctly; signal accuracy is tunable for game balance.

---

## 3. Disadvantages
- **Signal Accuracy**: Signal is not perfect—accuracy is configurable (e.g., 66% correct).
- **Standard Fee Structure**: Only standard fees (+\$0.01 maker / -\$0.02 taker) vs. Market Makers' enhanced rates.
- **No Market Making**: Cannot quote two-sided markets, limiting ability to capture spreads.
- **Position Limits**: Hard limits prevent excessive positions (150 per option, 500 total).
- **Complexity**: Must research and implement multiple strategies (volatility, direction, spreads).
- **Single-Sided Only**: Restricted to single-sided limit orders or market orders.
- **Risk Management**: Must handle false signals appropriately to avoid losses.

---

## 4. Suggested Strategies

### Strategic Implications of No Market Making:
- **Focus on Directional Alpha**: Without ability to quote spreads, must generate profits from correct market predictions.
- **Aggressive Positioning**: Use signal edge to take larger, more confident positions before events.
- **Liquidity Taking**: Accept taker fees when necessary to capture time-sensitive opportunities.
- **Volatility Plays**:  
  - Use the probability transition matrix to position before regime shifts:
    - If signal predicts low to high vol transition: Buy straddles/strangles
    - If signal predicts high to low vol transition: Sell premium
  - Size positions based on transition probabilities and signal accuracy.

- **Directional Bets**:  
  - Use regime predictions to anticipate market moves:
    - Higher vol often correlates with larger price swings
    - Position accordingly with the advance warning

- **Probability-Weighted Strategies**:
  - Use the full transition matrix to create sophisticated strategies:
    - Weight positions by probability of each outcome
    - Hedge against lower-probability but high-impact transitions

- **Cross-Product Spreads**:  
  - Trade SPX vs. SPY options to capture tracking-error anomalies (when not handled by Arb Desk).
  - Use vol regime predictions to time entry/exit of spread trades.

---

## 5. Bonus Challenge
- **Optimize Signal Usage & Risk Management**  
  1. Track the accuracy of your advance signals vs. actual regime changes.
  2. Analyze the probability transition matrices to identify patterns.
  3. Develop a position sizing algorithm that accounts for:
     - Signal accuracy (configurable, e.g., 66%)
     - Transition probabilities from the matrix
     - Current volatility state
  4. Measure P&L per correct vs. incorrect signal to refine strategy.

---
