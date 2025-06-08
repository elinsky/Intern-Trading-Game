"""Main entry point for the Intern Trading Game API."""

import uvicorn

from .infrastructure.api.app import create_app

# Create the FastAPI app
app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)  # nosec B104
