# Role: Arbitrage Desk

## One-Line Mission

Spot pricing mismatches between SPX and SPY, capturing small, consistent profits as prices converge.

---

## 1. Role Details

- **Signal Access**: Instant SPX–SPY tracking-error signal with 80% accuracy (e.g., "SPY overpriced vs SPX by 0.15").
- **Fees/Incentives**:
  - **Standard Maker Rebate**: +\$0.01 per filled side.
  - **Standard Taker Fee**: -\$0.02 per executed contract.
  - **Extra Points**: Scoring bonus for successful round-trip trades that net out risk.
- **Constraints**:
  - SPX and SPY positions must be roughly balanced (within 2:1 ratio).
  - Position limits: Maximum 100 contracts per leg of paired trades.
- **Scoring Focus**:
  - **Signal P&L**: Profit/loss when trading on tracking error signals
  - **Balance Ratio**: Penalty if SPX/SPY positions exceed 2:1 ratio
  - **Signal Response Time**: Bonus for acting within 1 tick of signal

---

## 2. Advantages

- **Signal Edge**: Instantaneous tracking-error data provides early entry advantage.
- **Execution Choice**: Can quote passively for rebates or take aggressively when opportunity is large.
- **Immediate Signals**: Tracking error signal arrives instantly.
- **Balanced Exposure**: Paired trades limit directional risk—stable, low-risk edge.

---

## 3. Disadvantages

- **Balance Requirement**: Must maintain balanced SPX/SPY positions within 2:1 ratio.
- **Small Margins**: Reliant on thin mispricings; profits per trade are minimal.

---

## 4. How to Make Money

1. **Understand the Tracking-Error Signal**
   - Signal shows realized volatility divergence between SPX and SPY
   - E.g., "SPY tracking error +0.15" means SPY is moving more than expected vs SPX
   - In efficient markets, this realized vol difference should impact option prices

2. **Identify Option Mispricings**
   - Higher realized vol in SPY → SPY options should be priced higher
   - If options don't reflect this difference, arbitrage opportunity exists
   - Compare same-strike options between SPX and SPY

3. **Execute the Arbitrage**
   - If SPY showing excess realized vol but options equally priced:
     - **Buy** SPY options (underpriced given higher realized vol)
     - **Sell** SPX options (overpriced given lower realized vol)
   - Maintain position balance within 2:1 ratio

4. **Capture the Convergence**
   - As market recognizes the vol difference, option prices adjust
   - Close both legs when pricing normalizes
   - Profit from the option repricing, not underlying convergence

---

## 5. Suggested Strategies

- **React to Signal Immediately**: With 80% accuracy and instant delivery, act fast when tracking error appears
- **Trade the Vol Difference**: If SPY shows higher realized vol, buy SPY options and sell SPX options at same strikes
- **Size Based on Signal Strength**: Larger tracking errors should drive larger positions (within 2:1 limits)
- **Monitor for Convergence**: Close positions when either tracking error normalizes OR option prices adjust
- **Use Multiple Strikes**: Spread trades across different strikes to capture the full volatility surface adjustment

---
