"""Console entry point for the local development API."""

import uvicorn


def run() -> None:
    uvicorn.run("xpoker_agent.api:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    run()
