# Documentation for Intern Trading Game

This directory contains the documentation for the Intern Trading Game project. The documentation is built using [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) with [mkdocstrings](https://mkdocstrings.github.io/) for automatic API documentation generation from docstrings.

## Structure

The documentation follows a four-quadrant structure:


1. **Tutorials**: Step-by-step guides to help you get started with the Intern Trading Game.
2. **How-To Guides**: Practical guides for accomplishing specific tasks.
3. **Reference**: Detailed API documentation and technical specifications.
4. **Explanation**: In-depth explanations of concepts and design decisions.

## Building the Documentation

### Local Development

To build and serve the documentation locally:


1. Install the required dependencies:

```bash
pip install -e ".[docs]"
```

2. Serve the documentation locally:

```bash
mkdocs serve
```

This will start a local server at http://127.0.0.1:8000/ that automatically rebuilds the documentation when files are changed.

3. Build the documentation:

```bash
mkdocs build
```

This will build the documentation to the `site` directory.

### GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch. This is handled by the GitHub Actions workflow in `.github/workflows/docs.yml`.

## Adding New Documentation

### Adding New Pages

1. Create a new Markdown file in the appropriate directory:

   - `tutorials/` for tutorials
   - `how-to/` for how-to guides
   - `reference/` for reference documentation
   - `explanation/` for explanations

2. Add the new page to the navigation in `mkdocs.yml`:

```yaml
nav:

  - Home: index.md
  - Tutorials:

      - Your New Tutorial: tutorials/your-new-tutorial.md
  # ...
```

### Documenting Code

The API reference documentation is automatically generated from docstrings in the code. To ensure your code is properly documented:


1. Use NumPy-style docstrings for all classes, methods, and functions.
2. Include the following sections in your docstrings:

   - Summary line
   - Extended description
   - Parameters
   - Returns or Yields
   - Raises (if applicable)
   - Attributes (for classes)
   - Notes (including mathematical derivations, formulas, citations)
   - TradingContext (for trading logic)
   - Examples

3. If you add a new module that should be included in the API reference, add it to the list in `docs/gen_ref_pages.py`.

## Customizing the Documentation

### Theme Customization

The theme is configured in `mkdocs.yml`. You can customize the colors, fonts, and other aspects of the theme by modifying the `theme` section.

### Extensions

The documentation uses several Markdown extensions to enhance the content:


- `admonition`: For adding notes, warnings, and other callouts
- `pymdownx.superfences`: For code blocks with syntax highlighting
- `pymdownx.arithmatex`: For LaTeX math support
- And more...

You can add or remove extensions in the `markdown_extensions` section of `mkdocs.yml`.
