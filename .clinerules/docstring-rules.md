# Code Documentation Rule – “Quant and Business Logic Modules require rich docstrings”

## Purpose
Complex quantitative algorithms and domain‑specific business logic must be understandable years from now by new developers, quants, and auditors.
We therefore require **professional‑quality docstrings**, comparable to scikit‑learn’s style, on all such code.

---

## Required docstring structure
Use **numpydoc / scikit‑learn** formatting with the following sections **in order** (omit a section only if genuinely not applicable):

1. **Summary line** – one sentence.
2. **Extended description** – multi‑paragraph overview of the algorithm or business rule.
3. **Parameters** – `name : type, default=<val>` with explanations.
4. **Returns** or **Yields** – shape / type and meaning.
5. **Raises** – exceptions triggered by invalid input (optional).
6. **Attributes** – for classes.
7. **Notes** – include mathematical derivations, formulas (LaTeX `r"$\sigma = \sqrt{…}$"`), citations, or regulatory references.
8. **TradingContext** – market assumptions, trading venue rules, risk parameters, volatility regimes, and any simulation-specific constraints (required for trading logic; optional for pure math).
9. **Examples** – runnable code snippets with expected output, demonstrating realistic trading scenarios.

### Minimum length
* Docstring body (lines after the summary) must be **≥ 10 non‑blank lines**.

### Formatting details
* Use reST section headers with a line of dashes:

      Parameters
      ----------
* Align types and descriptions vertically as in scikit‑learn.
* Wrap lines at ≤ 88 characters.
* Inline math using LaTeX. Longer derivations may be indented as::

      .. math::

         V = e^{-rT} \mathbb{E}[(S_T - K)^+]

* Reference academic papers or manuals with BibTeX‑style citations in “Notes”.

---

## Enforcement checklist (evaluated by Cline)
1. For each public object lacking a docstring or with < 10 non‑blank lines, fail.
2. Parse docstring text and verify presence (case‑insensitive) of required section headers (`Parameters`, `Returns` or `Yields`, and either `Notes` or `TradingContext`, plus `Examples`).
3. CI job `docstring-enforce` runs `/scripts/ci/enforce_docstrings.py`. Exit 1 on violation.
4. Override allowed only with commit footer:

       #docstring-override: true

   Overrides must be explained in MR description and approved by a code owner.

---

## Author‑facing snippet
Create a scaffolded docstring with:

    cline /snippet new-docstring

The snippet inserts the full section skeleton ready for filling.

---

## Continuous integration integration
* Pre‑commit hook **pydocstyle‑quant** runs `pydocstyle` with a custom config rejecting missing sections.
* CI job **docstring-enforce** uses a regex heuristic plus `numpydoc` validation.

---

## Living rule
Amend this rule if directory layouts change or if we adopt a different docstring standard.
