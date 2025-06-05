# Mathematical Formula Examples

This reference document provides examples of common mathematical formulas used in the Intern Trading Game project. You can copy these examples and adapt them for your own documentation needs.

## Basic Formulas

### Price-Time Priority

```markdown
$$\text{Priority} = (\text{Price}, \text{Time})$$
```

Renders as:

$$\text{Priority} = (\text{Price}, \text{Time})$$

### Simple Interest

```markdown
$$\text{Interest} = \text{Principal} \times \text{Rate} \times \text{Time}$$
```

Renders as:

$$\text{Interest} = \text{Principal} \times \text{Rate} \times \text{Time}$$

## Financial Formulas

### Black-Scholes Option Pricing

```markdown
$$C = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

$$d_2 = d_1 - \sigma\sqrt{T}$$
```

Renders as:

$$C = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

$$d_2 = d_1 - \sigma\sqrt{T}$$

### Put-Call Parity

```markdown
$$C - P = S_0 e^{-qT} - K e^{-rT}$$
```

Renders as:

$$C - P = S_0 e^{-qT} - K e^{-rT}$$

### Implied Volatility

```markdown
$$\text{Market Price} = f(S, K, r, q, T, \sigma_{\text{implied}})$$
```

Renders as:

$$\text{Market Price} = f(S, K, r, q, T, \sigma_{\text{implied}})$$

## Risk Metrics

### Delta

```markdown
$$\Delta = \frac{\partial V}{\partial S}$$
```

Renders as:

$$\Delta = \frac{\partial V}{\partial S}$$

### Gamma

```markdown
$$\Gamma = \frac{\partial^2 V}{\partial S^2}$$
```

Renders as:

$$\Gamma = \frac{\partial^2 V}{\partial S^2}$$

### Theta

```markdown
$$\Theta = \frac{\partial V}{\partial T}$$
```

Renders as:

$$\Theta = \frac{\partial V}{\partial T}$$

### Vega

```markdown
$$\text{Vega} = \frac{\partial V}{\partial \sigma}$$
```

Renders as:

$$\text{Vega} = \frac{\partial V}{\partial \sigma}$$

## Statistical Formulas

### Standard Deviation

```markdown
$$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}$$
```

Renders as:

$$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2}$$

### Correlation

```markdown
$$\rho_{xy} = \frac{\text{Cov}(X,Y)}{\sigma_X \sigma_Y}$$
```

Renders as:

$$\rho_{xy} = \frac{\text{Cov}(X,Y)}{\sigma_X \sigma_Y}$$

## Matrix Notation

### Covariance Matrix

```markdown
$$\Sigma =
\begin{pmatrix}
\sigma_1^2 & \sigma_{12} & \cdots & \sigma_{1n} \\
\sigma_{21} & \sigma_2^2 & \cdots & \sigma_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
\sigma_{n1} & \sigma_{n2} & \cdots & \sigma_n^2
\end{pmatrix}$$
```

Renders as:

$$\Sigma =
\begin{pmatrix}
\sigma_1^2 & \sigma_{12} & \cdots & \sigma_{1n} \\
\sigma_{21} & \sigma_2^2 & \cdots & \sigma_{2n} \\
\vdots & \vdots & \ddots & \vdots \\
\sigma_{n1} & \sigma_{n2} & \cdots & \sigma_n^2
\end{pmatrix}$$

## Inline Math Examples

When you need to include math within a paragraph, use the inline syntax:

```markdown
The delta of an option \(\Delta\) measures the rate of change of the option price with respect to the price of the underlying asset.
```

Renders as:

The delta of an option \(\Delta\) measures the rate of change of the option price with respect to the price of the underlying asset.

## Using Math in Docstrings

When adding math to Python docstrings, **always use raw strings** (prefixed with `r`) and maintain proper indentation:

```python
def calculate_option_price(S, K, r, q, T, sigma):
    r"""
    Calculate the price of a European call option using the Black-Scholes formula.

    The Black-Scholes formula is:

    $$C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

    where:

    $$d_1 = \frac{\ln(S/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

    $$d_2 = d_1 - \sigma\sqrt{T}$$

    Parameters
    ----------
    S : float
        Current price of the underlying asset
    K : float
        Strike price
    r : float
        Risk-free interest rate (annualized)
    q : float
        Dividend yield (annualized)
    T : float
        Time to expiration (in years)
    sigma : float
        Volatility of the underlying asset (annualized)

    Returns
    -------
    float
        Price of the European call option
    """
```

### Why Raw Strings Are Required

Without the `r` prefix, Python interprets backslashes as escape sequences:

- `\t` becomes a tab character
- `\f` becomes a form feed character
- `\n` becomes a newline

This breaks LaTeX commands like `\text`, `\frac`, and `\sqrt`, causing formulas to render incorrectly.

For example, without a raw string:
```python
"""
$$\text{Value} = \text{Price} \times \text{Quantity}$$
"""  # Will render as "extValue = extPrice × extQuantity"
```

With a raw string:
```python
r"""
$$\text{Value} = \text{Price} \times \text{Quantity}$$
"""  # Will render correctly
```

## Resources

For more information on using math in documentation:


- [MathJax Documentation](https://docs.mathjax.org/)
- [LaTeX Math Symbols Cheat Sheet](https://www.caam.rice.edu/~heinken/latex/symbols.pdf)
- [Detexify](https://detexify.kirelabs.org/classify.html) - Draw a symbol to find its LaTeX command
