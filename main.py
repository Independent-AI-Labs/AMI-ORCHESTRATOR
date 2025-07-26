"""
Main entry point for the Orchestrator.
"""

from orchestrator.api import app


def main():
    """Main function."""
    print("Orchestrator started.")
    app.run(port=8080)


if __name__ == "__main__":
    main()
