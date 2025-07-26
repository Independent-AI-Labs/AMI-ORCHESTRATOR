"""
Sample adapter that runs the Gemini CLI adapter.
"""

from orchestrator.acp.gemini_acp_protocol import InitializeParams, SendUserMessageParams
from orchestrator.acp.gemini_cli_adapter import GeminiCliAdapter


def main():
    """Main function for the sample adapter."""
    adapter = GeminiCliAdapter("C:\\Users\\vdonc\\AMI-SDA\\orchestrator\\gemini-cli\\bundle\\gemini.js")
    adapter.initialize(InitializeParams(protocol_version="0.0.9"))
    adapter.send_user_message(SendUserMessageParams(chunks=[{"text": "Hello, world!"}]))


if __name__ == "__main__":
    main()
