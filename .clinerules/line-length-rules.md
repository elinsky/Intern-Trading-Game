# Code Style Rule – "All Code Must Be 79 Characters or Less"

## Purpose
Code readability and maintainability are enhanced when lines are kept to a reasonable length.
A strict 79-character limit ensures code is easily viewable on all screen sizes, in side-by-side
diffs, and in terminal environments without wrapping. This rule enforces PEP 8's original
recommendation for maximum line length.

---

## When does this rule apply?
This rule applies to **all** of the following:

- Python source code (`.py` files)
- Documentation (`.md`, `.rst`, etc.)
- Docstrings within Python code
- Comments within code
- Configuration files (`.toml`, `.yaml`, etc.)
- Any other text files in the repository

---

## Required formatting
For all text in the repository:

1. **Maximum line length**: 79 characters
2. **No exceptions**: Even for URLs, table formatting, or other special cases
3. **Consistent indentation**: 4 spaces for Python code, 2 spaces for YAML/markdown
4. **Line breaks**: Use appropriate line continuation techniques:
   - Backslashes for explicit line continuation
   - Parentheses for expression continuation
   - Triple quotes for multi-line strings
   - Hanging indents for continued lines

### Examples

#### Good: Python code with proper line breaks

```python
def calculate_position_value(
    quantity, price, multiplier=1.0, currency_conversion=1.0
):
    """Calculate the monetary value of a trading position.

    The value is determined by multiplying quantity, price, contract
    multiplier, and any currency conversion factor.
    """
    return quantity * price * multiplier * currency_conversion
```

#### Bad: Line exceeding 79 characters

```python
def calculate_position_value(quantity, price, multiplier=1.0, currency_conversion=1.0):
    """Calculate the monetary value of a trading position. The value is determined by multiplying quantity, price, contract multiplier, and any currency conversion factor."""
    return quantity * price * multiplier * currency_conversion
```

---

## Enforcement checklist (evaluated by Cline)
1. Detect any lines exceeding 79 characters in any file.
2. Verify that docstrings, comments, and documentation adhere to the same limit.
3. Fail the commit with guidance if any line exceeds the limit.
4. Allow override only when the commit footer contains:

       #line-length-override: true

   Overrides must be justified in the commit message and approved by a code owner.

---

## Author‑facing snippet
Format long lines with:

    cline /snippet format-long-line

The snippet inserts appropriate line breaks based on context.

---

## Continuous integration integration
- Pre‑commit hook **ruff** and **ruff-format** enforce the 79-character limit for Python code.
- CI job **line-length-enforce** runs `/scripts/ci/enforce_line_length.sh` to check all files.
  The script exits status 1 on violation.

---

## Living rule
This rule supersedes any conflicting line length specifications in other rules or documentation.
The 79-character limit is now the standard across all project files.
