# Role: Hedge Fund

## One-Line Mission
Keep implied volatility aligned with realized volatility by trading gamma before regime changes.

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
  - **Delta Neutrality**: Must maintain portfolio delta within ±50 deltas at each tick.
  - **Rehedging Required**: Must adjust underlying position when delta exceeds limits.
- **Scoring Focus**:
  - **Window P&L**: Total profit/loss from event to event (complete regime cycles)
  - **Rehedging Profits**: P&L specifically from delta hedging trades
  - **Delta Penalty**: Deduction for exceeding ±50 delta limit per tick

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
1. **Understand Your Edge**
   - You know when realized volatility will change (with advance warning)
   - Your job: ensure implied volatility reflects upcoming realized volatility
   - Profit by trading gamma before the regime change occurs

2. **Trade Based on Regime Direction**
   - **Low to High Vol**: Buy options now, gamma scalp during high vol period
   - **High to Low Vol**: Sell options now, collect premium as vol normalizes
   - Between events, realized vol stabilizes at new level

3. **Gamma Trading Strategy**
   - **Long Gamma** (bought options): Must rehedge as underlying moves - buy low, sell high
   - **Short Gamma** (sold options): Must rehedge to stay neutral - sell high, buy low
   - **Delta Constraint**: ±50 delta limit forces continuous rehedging
   - Your advance signal lets you position gamma before others adjust IV

4. **Event-to-Event Windows**
   - Each regime lasts from one news event to the next
   - Realized vol normalizes quickly after regime change
   - Performance measured over these complete windows

---

## 5. Suggested Strategies
- **Gamma Positioning**: Long gamma before high vol periods, short gamma before low vol
- **Delta-Neutral Entry**: Start with straddles/strangles to isolate volatility exposure
- **Active Rehedging**: In high vol, rehedge frequently to capture gamma profits
- **Premium Collection**: In low vol, focus on theta decay from sold options
- **Window-Based P&L**: Measure success over complete event-to-event cycles

---
