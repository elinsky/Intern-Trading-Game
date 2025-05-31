# Documentation Rule – “Feature Commits must ship Docs”

## Why this rule exists
Good software fails without good documentation.
Every new capability must be discoverable, learnable, and maintainable by others.
Therefore, any change that **adds a feature** **must** include matching documentation.

---

## When does this rule apply?
A commit (or MR/PR) is considered a **Feature Commit** if **any** of the following are true:

- The commit message starts with `feat:` or `feature:`
- A new file is added under `/src`
- An existing source file’s public interface changes (for example, function, class, route, CLI command)

If a Feature Commit is detected, the checks below are required.
Non‑feature commits (fixes, refactors, CI tweaks, and similar) are exempt **only** when the commit message begins with `chore:` or `fix:` and contains the token `#docs-none`.

---

## Required documentation artifacts
For each Feature Commit, **at least one file in `/docs/**` must be added or updated**, following the **Four Quadrants** structure:

| Quadrant         | Purpose                                   | File location        | Typical filename pattern                   |
| ---------------- | ----------------------------------------- | -------------------- | ------------------------------------------ |
| **Tutorial**     | Help a newcomer get started               | `/docs/tutorials/`   | `<role>-tutorial.md`                       |
| **How‑to guide** | Step‑by‑step to accomplish a goal         | `/docs/how-to/`      | `how-to-<verb>-<feature>.md`               |
| **Reference**    | Dry, authoritative API/config details     | `/docs/reference/`   | `<feature>.md`                             |
| **Explanation**  | Why it works, design, trade‑offs, context | `/docs/explanation/` | `explaining-<feature>.md` or ADR reference |

**Minimum bar:** one of the four documents per new feature.
**Gold standard:** all four quadrants, updated CHANGELOG, and README cross‑links.

---

## Enforcement checklist (evaluated by Cline)
1. Detect feature commit (rules above).
2. Verify documentation:
   - At least **one** file in `/docs/**` is **added** or **modified** in the same commit.
   - That file path matches one of the quadrant folders.
3. Fail the commit with an actionable message if the criteria aren’t met.
4. Allow override only when the commit includes the footer line:

       #docs-override: true

   Overrides must be explained in MR description and approved by a code owner.
