# Glossary of Terms

## A

**Alpha**: Excess return above a benchmark or risk-free rate. In this game, refers to trading edge from signals or strategy.

**Arbitrage**: Simultaneous purchase and sale of related instruments to profit from price discrepancies. The Arbitrage Desk role specializes in SPX-SPY convergence trades.

**Ask**: The price at which a seller is willing to sell. Also called the "offer."

**At-the-money (ATM)**: An option whose strike price equals the current underlying price.

## B

**Backtesting**: Testing a trading strategy on historical data to evaluate its performance.

**Beta**: Measure of systematic risk relative to the market. Arbitrage desks target beta-neutral positions.

**Bid**: The price at which a buyer is willing to buy.

**Bid-Ask Spread**: The difference between the bid and ask prices. Market makers profit from this spread.

**Black-Scholes**: Mathematical model for pricing European options, used in the simulation.

## C

**Call Option**: Contract giving the right to buy the underlying at the strike price at expiration.

**Circuit Breaker**: Maximum price movement allowed per tick (5% in this game).

**Convergence Trade**: Arbitrage strategy betting that prices will converge to fair value.

**Correlation**: Statistical relationship between two assets. SPX-SPY correlation is ~0.98.

## D

**Delta**: Rate of change of option price with respect to underlying price movement.

**Directional Trading**: Taking positions based on expected market direction (Hedge Fund specialty).

**Drawdown**: Peak-to-trough decline in portfolio value.

## E

**European Option**: Option that can only be exercised at expiration (used in this game).

**Execution Risk**: Risk that trades won't execute at expected prices.

**Expected Value**: Probability-weighted average of possible outcomes.

## F

**Fill**: Successful execution of an order.

**Fill Rate**: Percentage of orders that execute successfully.

## G

**Gamma**: Rate of change of delta with respect to underlying price.

**Geometric Brownian Motion (GBM)**: Mathematical model for price evolution used in the simulation.

**Greeks**: Sensitivity measures for options (Delta, Gamma, Vega, Theta).

## H

**Hedge**: Position taken to reduce risk in another position.

**Hit Rate**: Percentage of profitable trades or signals.

## I

**Implementation Shortfall**: Difference between decision price and execution price.

**Implied Volatility (IV)**: Market's expectation of future volatility embedded in option prices.

**Inventory Risk**: Risk from holding positions (critical for market makers).

**In-the-money (ITM)**: Call with strike below spot, or put with strike above spot.

## K

**Kelly Criterion**: Formula for optimal position sizing based on edge and odds.

**KPI (Key Performance Indicator)**: Primary metrics used for scoring each role.

## L

**Leg**: One side of a paired trade (e.g., SPX leg and SPY leg).

**Limit Order**: Order to buy/sell at a specific price or better.

**Liquidity**: Ease of trading without moving the price. Market makers provide liquidity.

## M

**Maker**: Order that adds liquidity to the order book (earns rebate).

**Market Order**: Order to buy/sell immediately at best available price.

**Mark-to-Market**: Valuing positions at current market prices.

**Mean Reversion**: Tendency for prices to return to average levels.

**Microstructure**: Study of how markets operate at the order and trade level.

**Moneyness**: Relationship between option strike and underlying price.

## N

**Net Position**: Long positions minus short positions.

**Noise**: Random price movements without information content.

## O

**Order Book**: List of all resting buy and sell orders.

**Out-of-the-money (OTM)**: Call with strike above spot, or put with strike below spot.

## P

**P&L (Profit and Loss)**: Financial performance measure.

**Paired Trade**: Simultaneous positions in related instruments (Arbitrage Desk requirement).

**Position Limit**: Maximum allowed position size per instrument or portfolio.

**Price-Time Priority**: Order matching rule giving preference to better prices, then earlier orders.

**Put Option**: Contract giving the right to sell the underlying at the strike price.

## Q

**Quote**: Two-sided market showing both bid and ask (Market Maker requirement).

**Quote Stuffing**: Prohibited practice of submitting excessive orders to slow the system.

## R

**Realized Volatility (RV)**: Actual price volatility that occurs.

**Rebate**: Payment for providing liquidity (making).

**Regime**: Market state (low/medium/high volatility in this game).

**Risk-Adjusted Return**: Return accounting for risk taken (e.g., Sharpe ratio).

## S

**Sharpe Ratio**: Risk-adjusted return measure (return per unit of volatility).

**Signal**: Information advantage provided to specific roles.

**Slippage**: Difference between expected and actual execution price.

**Spread**: Difference between bid and ask prices.

**Strike Price**: Price at which option can be exercised.

## T

**Taker**: Order that removes liquidity from the book (pays fee).

**Theta**: Time decay of option value.

**Tick**: 5-minute interval when prices update and trades occur.

**Tracking Error**: Deviation of SPY from theoretical SPX/10 value.

**Two-Sided Quote**: Simultaneous bid and ask prices (Market Maker only).

## U

**Underlying**: The asset on which derivatives are based (SPX and SPY).

**Uptime**: Percentage of time actively quoting (Market Maker requirement: 80%).

## V

**Vega**: Sensitivity of option price to volatility changes.

**Volatility**: Standard deviation of returns, measuring price variability.

**Volatility Arbitrage**: Trading implied vs realized volatility differences.

**Volatility Regime**: Market state of low/medium/high volatility.

**Volatility Smile/Skew**: Pattern of implied volatilities across strikes.

**Volume**: Number of contracts traded.

## W

**Working Order**: Order resting in the book waiting to fill.

## Z

**Z-Score**: Number of standard deviations from mean, used for mean reversion signals.

## Common Abbreviations

- **API**: Application Programming Interface
- **ATM**: At-the-money
- **GBM**: Geometric Brownian Motion
- **HF**: Hedge Fund
- **ITM**: In-the-money
- **IV**: Implied Volatility
- **MM**: Market Maker
- **OTM**: Out-of-the-money
- **RV**: Realized Volatility
- **SPX**: S&P 500 Index
- **SPY**: S&P 500 ETF

## Role-Specific Terms

### Market Maker Terms
- **Inventory Management**: Controlling position size to stay within limits
- **Quote Coverage**: Percentage of instruments actively quoted
- **Spread Capture**: Profit from bid-ask spread
- **Enhanced Rebate**: +$0.02 maker rebate (2x normal)

### Hedge Fund Terms
- **Directional Bias**: Taking long or short positions
- **Signal Trading**: Using volatility forecasts to trade
- **Volatility Edge**: Profit from IV vs RV differences
- **Position Concentration**: Large positions in fewer instruments

### Arbitrage Desk Terms
- **Convergence Trade**: Betting on price relationships normalizing
- **Paired Position**: Balanced SPX and SPY trades
- **Tracking Signal**: Alert when SPY diverges from SPX
- **Market Neutral**: No directional exposure

## Trading Mechanics Terms

- **Batch Processing**: All orders processed simultaneously per tick
- **Order Window**: 2-3 minute period to submit orders
- **Price Discovery**: Process of finding equilibrium prices
- **Tick Processing**: 5-minute cycle of price generation and trading