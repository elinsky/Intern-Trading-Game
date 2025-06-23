"""Generate the API reference pages."""

from pathlib import Path

import mkdocs_gen_files

# Define the modules to document
modules = [
    "intern_trading_game.domain.exchange.components.orderbook.book",
    "intern_trading_game.domain.exchange.components.core.models",
    "intern_trading_game.domain.exchange.components.core.types",
    "intern_trading_game.domain.exchange.venue",
    "intern_trading_game.domain.exchange.response.coordinator",
    "intern_trading_game.domain.exchange.response.interfaces",
    "intern_trading_game.domain.exchange.response.models",
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
