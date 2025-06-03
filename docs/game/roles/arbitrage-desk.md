# Role: Arbitrage Desk

## One-Line Mission
Spot pricing mismatches between SPX and SPY, capturing small, consistent profits as prices converge.

---

## 1. Role Details
- **Signal Access**: Instant SPX–SPY tracking-error signal with 80% accuracy (e.g., “SPY overpriced vs SPX by 0.15”).
- **Fees/Incentives**:
  - **Standard Maker Rebate**: +\$0.01 per filled side.
  - **Standard Taker Fee**: -\$0.02 per executed contract.
  - **Extra Points**: Scoring bonus for successful round-trip trades that net out risk.
- **Constraints**:
  - Must submit paired trades: SPX and SPY positions must be roughly balanced (within 2:1 ratio).
  - Position limits: Maximum 100 contracts per leg of paired trades.
- **Scoring Focus**:
  - Profit from spread convergence.
  - Precision of execution (fill rates, slippage).
  - Frequency of profitable round-trip trades.

---

## 2. Advantages
- **Signal Edge**: Instantaneous tracking-error data provides early entry advantage.
- **Execution Choice**: Can quote passively for rebates or take aggressively when opportunity is large.
- **Immediate Signals**: Tracking error signal arrives instantly.
- **Balanced Exposure**: Paired trades limit directional risk—stable, low-risk edge.

---

## 3. Disadvantages
- **Paired Trade Requirement**: Must maintain balanced SPX/SPY positions - no single-product trades.
- **Small Margins**: Reliant on thin mispricings; profits per trade are minimal.
- **Limited by Product Scope**: Only cross-product spreads allowed, no single-leg directional or vol trades.
- **No News Edge**: Cannot directly trade off news; must wait for tracking signals.

---

## 4. How to Make Money
1. **Use the Tracking-Error Signal**
   - E.g., signal: “SPY overpriced vs SPX by 2.5 points.”
   - Think: SPY call at 440 strike is richer than SPX call.

2. **Construct a Paired Options Trade**
   - **Sell** SPY call at 440.
   - **Buy** SPX call at 440.
   - Quantities should be roughly balanced between SPX and SPY.

3. **Wait for Mean Reversion**
   - As SPX and SPY realign, relative value converges.
   - Close both legs to lock in mispricing profit.

---

## 5. Suggested Strategies
- **Signal‐Driven Entries**: Use instantaneous tracking-error feed to jump in as soon as divergence occurs.
- **Rapid Execution**: Place limit orders just inside the spread to capture the mispricing without crossing too wide.
- **Position Balancing**: Adjust positions to maintain SPX/SPY balance within 2:1 ratio.
- **High-Frequency Pairing**: Continuously scan option pairs for micro-arbitrage in multiple strikes/expirations.

---

## 6. Bonus Challenge
- **Calibrate SPX–SPY Divergence Threshold**
  1. Analyze historical tracking-error values to identify mean and standard deviation.
  2. Set an entry rule (e.g., divergence > 1.5σ) and back-test P&L.
  3. Compute optimal threshold that maximizes sharpe ratio under realistic fill rates.

---
