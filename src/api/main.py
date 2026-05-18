from __future__ import annotations

import uvicorn

from src.api.app import app
from src.api.config import get_api_settings


def main():
    settings = get_api_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
