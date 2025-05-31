## Brief overview
This set of guidelines outlines Python coding style preferences for the Intern Trading Game project. These rules ensure consistent, readable, and maintainable code across the codebase.

## Code formatting
- Never let a logical line exceed 79 characters
- Prefer hanging indents to backslashes if a wrap is unavoidable
- Follow PEP 8 style guidelines for Python code
- Use 4 spaces for indentation (no tabs)

## Project structure
- Organize code into logical modules within the intern_trading_game package
- Keep related functionality in dedicated subpackages (e.g., exchange, instruments)
- Use clear, descriptive module and class names that reflect their purpose

## Documentation
- Include verbose docstrings for all modules, classes, and functions
- Emphasize both the business/trading and quant understanding when writing documentation
- Use triple double quotes (""") for docstrings
- Provide clear descriptions of parameters, return values, and exceptions

## Testing
- Write unit tests for all functionality
- Place tests in the tests directory with a corresponding structure to the main package
- Use pytest for running tests

## Development workflow
- Use pre-commit hooks for code quality checks
- Follow the development dependencies specified in pyproject.toml
- Ensure all code passes linting and type checking before committing
