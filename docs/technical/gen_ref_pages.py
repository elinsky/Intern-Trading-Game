"""Generate the API reference pages."""

from pathlib import Path

import mkdocs_gen_files

# Define the modules to document
modules = [
    "intern_trading_game.domain.exchange.book.order_book",
    "intern_trading_game.domain.exchange.core.order",
    "intern_trading_game.domain.exchange.core.trade",
    "intern_trading_game.domain.exchange.venue",
    "intern_trading_game.domain.exchange.core.instrument",
]

# Generate the API reference pages
for module in modules:
    module_path = module.replace(".", "/")
    doc_path = Path("reference", f"{module.split('.')[-1]}.md")

    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(f"# {module.split('.')[-1].title()}\n\n")
        f.write(f"::: {module}\n")

    mkdocs_gen_files.set_edit_path(
        doc_path, Path("../") / f"src/{module_path}.py"
    )
