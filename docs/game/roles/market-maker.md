# Role: Market Maker

## One-Line Mission
Quote fair, tight spreads and profit on every fill—while managing inventory within strict limits.

---

## 1. Role Details
- **Signal Access**: None.
- **Fees/Incentives**:
  - **Enhanced Maker Rebate**: +\$0.02 per filled side.
  - **Reduced Taker Fee**: -\$0.01 per contract.
  - **Competitive Advantage**: Enhanced fee structure vs. other roles (+\$0.02 maker vs. +\$0.01 for HF/Arb).
- **Constraints**:
  - Must quote ≥ 80 % of instruments across BOTH SPX and SPY each tick.
  - Inventory limits: Maximum ±50 net contracts per product (SPX/SPY).
  - Must provide two-sided quotes (bid and ask) on each instrument.
- **Scoring Focus**:
  - Spread capture per trade.
  - Quote uptime (percentage of time with active quotes).
  - Inventory risk management (staying within ±50 net position limits).
  - Quoting coverage (≥ 80 %).

---

## 2. Advantages
- **Guaranteed Flow**: Always in the market with posted quotes for consistent spread capture.
- **Superior Fee Structure**: Enhanced maker rebates (+\$0.02) and reduced taker fees (-\$0.01) provide significant cost advantage.
- **Direct Competition**: Both MMs compete on same products, driving innovation and efficiency.
- **Inventory Control**: Can hedge to stay within position limits and minimize risk.
- **Predictable Edge**: Profits primarily from capturing the bid-ask spread.
- **Competition Dynamics**: While competing with another MM, the enhanced fee structure provides sustainable profitability.

---

## 3. Disadvantages
- **No Signal Edge**: Must infer volatility/direction from market data and retail flow.
- **Obligation to Quote**: ≥ 80 % coverage forces participation, even in adverse conditions.
- **MM vs MM Competition**: Direct competition with another Market Maker can compress spreads.
- **Dual Product Obligation**: Must maintain quotes on both SPX and SPY products simultaneously.

---

## 4. Suggested Strategies
- **Adaptive Spread**: Widen spreads in high-vol regimes; tighten in low-vol.
- **Retail Flow Exploitation**: Identify aggressive retail orders that cross wide spreads.
- **Inventory Management**: Use underlying futures/spot to stay within ±50 net position limits.
- **Inventory Skew Management**: Adjust quotes to steer inventory toward desired levels.
- **Inter-Product Risk Management**: Balance inventory across SPX and SPY positions.
- **Competitive Positioning**: Monitor competing MM's quotes and adjust spreads strategically while maintaining profitability through fee advantage.

---

## 5. Bonus Challenge
- **Estimate the Implied vs. Realized Vol Spread**
  Develop a simple model that:
  1. Tracks the difference between implied vol (IV) and realized vol (RV) for your assigned product.
  2. Adjusts spread widths dynamically when IV – RV widens beyond a threshold.

---
