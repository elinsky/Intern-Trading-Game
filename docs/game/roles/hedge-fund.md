# Role: Hedge Fund

## One-Line Mission
Detect mispriced implied volatility and use directional or volatility trades to capitalize on regime shifts.

---

## 1. Role Details
- **Signal Access**:
  - Receives advance warning a configurable number of ticks before news events
  - Signal includes:
    - **Regime Change Prediction**: Whether the news event will trigger a volatility regime change
    - **Probability Transition Matrix**: Shows transition probabilities from current state to next state
    - **Three Volatility States**: Low vol, medium vol, and high vol (all configurable)
    - **Signal Accuracy**: Configurable (e.g., 66% accuracy means signal is correct 66% of the time)
  - Signal timing is configurable (e.g., arrives 2 ticks before the actual news event)
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
  - **Signal P&L**: Profit/loss on positions opened within 5 ticks of signal
  - **Signal Hit Rate**: Percentage of profitable trades when acting on signals
  - **Position Penalty**: Deduction for exceeding position limits

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

## 4. How to Make Money
1. **Understand Your Signal**
   - You receive advance warning before volatility regime changes
   - Signal includes probability matrix showing likely transitions
   - With 66% accuracy, not every signal is correct - manage risk accordingly

2. **Position Before the Market**
   - Low to High Vol transition → Buy options (straddles/strangles) before vol spike
   - High to Low Vol transition → Sell options to capture premium decay
   - Use the advance warning time to build positions before others react

3. **Size Based on Probabilities**
   - Signal gives full transition matrix, not just binary prediction
   - Larger positions when probability is higher
   - Always account for 34% false signal rate in position sizing

4. **Execute and Exit**
   - Take liquidity when needed - your edge is timing, not spread capture
   - Exit when regime change materializes (or fails to)
   - Don't hold hoping for more - you profit from the transition, not the new regime

---

## 5. Suggested Strategies
- **Pre-Position for Vol Changes**: Use advance warning to buy/sell volatility before regime shifts
- **Focus on ATM Options**: These have highest vega and will move most on vol regime changes
- **Quick In, Quick Out**: Your edge is the advance warning - capture the initial move, don't overstay
- **Probability-Weight Positions**: If signal shows 70% chance of high vol, size accordingly
- **Accept False Signals**: With 66% accuracy, expect 1/3 of trades to be wrong - size to survive

---
