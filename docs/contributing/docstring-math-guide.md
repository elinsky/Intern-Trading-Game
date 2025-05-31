# Math Formulas in Docstrings

This guide explains how to properly include mathematical formulas in docstrings and documentation for the Intern Trading Game project.

## Using MathJax Syntax

All mathematical formulas in docstrings and Markdown documentation should use MathJax syntax with LaTeX notation. This ensures proper rendering in our documentation site.

### Inline Math

For inline math (within a paragraph), use `\(` and `\)` delimiters:

```markdown
The Black-Scholes formula uses \(\sigma\) to represent volatility.
```

Renders as: The Black-Scholes formula uses \(\sigma\) to represent volatility.

### Display Math

For display math (standalone equations), use `$$` delimiters:

```markdown
$$\text{Price} = S_0 e^{(r-q)T} N(d_1) - K e^{-rT} N(d_2)$$
```

Renders as:

$$\text{Price} = S_0 e^{(r-q)T} N(d_1) - K e^{-rT} N(d_2)$$

## Common Formatting Tips

1. **Text in Equations**: Use `\text{}` for words within equations:
   ```markdown
   $$\text{Priority} = (\text{Price}, \text{Time})$$
   ```

2. **Fractions**: Use `\frac{numerator}{denominator}`:
   ```markdown
   $$\text{Implied Volatility} = \frac{\text{Market Price}}{\text{Model Price}}$$
   ```

3. **Subscripts and Superscripts**: Use `_` for subscripts and `^` for superscripts:
   ```markdown
   $$S_0 \text{ and } e^{rT}$$
   ```

4. **Greek Letters**: Use the backslash followed by the name:
   ```markdown
   $$\alpha, \beta, \gamma, \delta, \sigma, \theta$$
   ```

## Incorrect Usage (Do Not Use)

### ❌ reStructuredText Directives

Do not use reStructuredText (reST) directives like `.. math::` in docstrings:

```python
# DON'T DO THIS
"""
.. math::

    Priority = (Price, Time)
"""
```

These will not render correctly in our MkDocs documentation.

### ❌ HTML Math

Do not use HTML-based math notation:

```html
<!-- DON'T DO THIS -->
<math>
  <mi>Priority</mi>
  <mo>=</mo>
  <mfenced>
    <mi>Price</mi>
    <mi>Time</mi>
  </mfenced>
</math>
```

## Examples from Our Codebase

### Price-Time Priority

```python
"""
The price-time priority rule is commonly used for order matching:

$$\text{Priority} = (\text{Price}, \text{Time})$$

Where better prices have higher priority, and for equal prices, earlier
orders have higher priority.
"""
```

### Option Pricing

```python
"""
The Black-Scholes formula for European call options:

$$C = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$

where:

$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$$

$$d_2 = d_1 - \sigma\sqrt{T}$$
"""
```

## Resources

- [MathJax Documentation](https://docs.mathjax.org/)
- [LaTeX Math Symbols Cheat Sheet](https://www.caam.rice.edu/~heinken/latex/symbols.pdf)
- For more examples, see our [Math Examples Reference](../reference/math-examples.md)
