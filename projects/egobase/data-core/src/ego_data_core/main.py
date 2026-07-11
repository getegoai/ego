"""Command entry point for the local Ego Data Core API."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.getenv("EGO_API_HOST", "127.0.0.1")
    port = int(os.getenv("EGO_API_PORT", "8765"))
    reload_enabled = os.getenv("EGO_RELOAD", "0").lower() in {"1", "true", "yes"}

    uvicorn.run(
        "ego_data_core.api.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()

