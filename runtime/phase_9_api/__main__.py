"""CLI entry point: python -m runtime.phase_9_api"""

from __future__ import annotations

import os

import uvicorn
from dotenv import load_dotenv

from runtime.phase_9_api.app import create_app

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000


def main() -> None:
    """
    Load environment variables and start the FastAPI server with uvicorn.
    """
    load_dotenv()
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
