# SPEC-SHELL-INTEGRATION: Terminal-Based Editor Integration for AMI-Agent

## Overview

This specification describes the integration of the terminal-based text editor (`scripts/cli_components/text_editor.py`) as the primary user interface for the `ami-agent` command. This creates a "think-in-editor" workflow where users can compose complex instructions in a proper text editor, then send them to AI agents with a simple key combination (Ctrl+S).

## Current State

- `ami-agent` is a CLI tool with various non-interactive modes (`--print`, `--audit`, `--tasks`, etc.)
- `scripts/cli_components/text_editor.py` provides a full-featured terminal-based text editor with Ctrl+S as the "save and exit" trigger
- The editor supports navigation, paste operations, and all standard text editing functionality

## Integration Plan

### 1. Default Editor Mode

When `ami-agent` is called without any arguments, it will:
- Launch the terminal-based text editor (`scripts/cli_components/text_editor.py`)
- Present an empty buffer for the user to compose instructions
- When the user presses `Ctrl+S` (EOF signal), capture the content and:
  - Send it to the AI agent in `--print` mode
  - Display the agent's response in the terminal

### 2. Implementation Details

#### 2.1. Streaming Output Architecture for Different Providers

The AMI Orchestrator already has a sophisticated architecture for handling different CLI implementations and their streaming output formats through the `CLIProvider` base class and provider-specific parser methods:

- Each provider (Claude, Qwen) inherits from `CLIProvider` and implements the `_parse_stream_message` method
- Claude CLI outputs JSON lines with `{"type": "content_block_delta", "delta": {"text": "chunk"}}`
- Qwen CLI would follow a similar pattern but may use different field names/structures
- The existing system properly handles provider-specific output structures through polymorphism

The `_parse_stream_message` method in each provider handles the unique JSON structure:

```python
def _parse_stream_message(
    self,
    line: str,
    cmd: list[str],
    line_count: int,
    agent_config: AgentConfig,
) -> tuple[str, dict[str, Any] | None]:
    """Parse a single line from CLI's streaming output."""
    output_text = ""
    metadata = None

    if not line.strip():
        return output_text, metadata

    try:
        # Try to parse as JSON first
        data = json.loads(line)
        if isinstance(data, dict):
            if "type" in data:
                msg_type = data["type"]
                # Claude pattern: content_block_delta with text in delta
                output_text = data.get("delta", {}).get("text", "") if msg_type == "content_block_delta" else ""
                # Generic fallback for text content
                if msg_type in ["content", "text"] and "text" in data:
                    output_text = data["text"]
                metadata = data
            else:
                output_text = json.dumps(data)
                metadata = None
        else:
            output_text = str(data)
            metadata = None
    except json.JSONDecodeError:
        output_text = line
        metadata = None

    return output_text, metadata
```

#### 2.2. Real-time Streaming Display for Editor Mode

To support real-time output display in the editor integration, we need to modify the streaming loop in `scripts/agents/cli/streaming.py` to support real-time output display:

```python
def run_streaming_loop_with_display(
    process: subprocess.Popen[str],
    cmd: list[str],
    agent_config: AgentConfigProtocol | None,
    provider_instance,  # The CLI provider instance with _parse_stream_message method
) -> tuple[str, dict[str, Any]]:
    """Run the main streaming loop with real-time output display."""
    full_output = ""
    started_at = time.time()

    session_id = agent_config.session_id if agent_config else "unknown"
    print(f"🔄 Agent session started: {session_id}")
    print("-" * 50)

    while True:
        # Calculate timeout for this read
        timeout_val = calculate_timeout(agent_config.timeout if agent_config else None, len(full_output))

        # Read a line with timeout
        line, is_timeout = read_streaming_line(process, timeout_val, cmd)

        if is_timeout:
            if agent_config and agent_config.timeout is not None:
                elapsed = time.time() - started_at
                if elapsed >= agent_config.timeout:
                    timeout_val = agent_config.timeout if agent_config else 0
                    timeout = agent_config.timeout or 0
                    raise AgentTimeoutError(timeout, cmd, elapsed)

            continue

        if line is None:
            if process.poll() is not None:
                break
            continue

        # Parse the line using the provider-specific parser
        if provider_instance:
            chunk_text, chunk_metadata = provider_instance._parse_stream_message(
                line, cmd, len(full_output), agent_config)

            # Display the chunk in real-time
            if chunk_text:
                print(chunk_text, end='', flush=True)
                full_output += chunk_text

            # Store metadata if needed
            if chunk_metadata:
                # Process provider-specific metadata
                pass
        else:
            # Fallback: just display the raw line
            print(line)
            full_output += line + "\n"

    print("\n" + "-" * 50)
    print("✅ Agent session completed")

    metadata = {
        "session_id": session_id,
        "duration": time.time() - started_at,
        "output_length": len(full_output),
    }
    return full_output, metadata
```

#### 2.3. Main CLI Enhancement (`scripts/agents/cli/main.py`)

Add a new default mode that triggers when no arguments are provided:

```python
def main() -> int:
    """Main entry point - Route to appropriate mode."""
    parser = argparse.ArgumentParser(
        description="AMI Agent - Unified automation entry point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ... existing arguments ...

    # New argument for editor mode
    parser.add_argument(
        "--interactive-editor",
        action="store_true",
        help="Interactive editor mode - opens text editor first, Ctrl+S sends to agent",
    )

    # ... rest of existing code ...

    args = parser.parse_args()

    # Route to appropriate mode using dispatch
    mode_handlers_list: list[tuple[str | bool | None, Callable[[], int]]] = [
        # ... existing handlers ...
        (args.interactive_editor, lambda: mode_interactive_editor() if args.interactive_editor else 1),
    ]

    for condition, handler in mode_handlers_list:
        if condition:
            return handler()

    # NEW: If no arguments provided, default to interactive editor mode
    if not any([
        args.print, args.hook, args.audit, args.tasks, args.sync, args.docs,
        args.interactive_editor
    ]):
        return mode_interactive_editor()

    # Show help if no mode specified
    parser.print_help()
    return 1
```

#### 2.4. Enhanced Interactive Editor Mode Handler (`scripts/agents/cli/mode_handlers.py`)

Add a new mode handler function that leverages the existing streaming architecture:

```python
def mode_interactive_editor() -> int:
    """Interactive editor mode - opens text editor first, Ctrl+S sends to agent.

    Args:
        None

    Returns:
        Exit code (0=success, 1=failure)
    """
    from scripts.cli_components.text_editor import TextEditor
    from scripts.agents.cli.factory import get_agent_cli
    from scripts.agents.cli.config import AgentConfigPresets
    from base.backend.utils.uuid_utils import uuid7

    print("📝 AMI Agent - Interactive Editor Mode")
    print("Compose your instruction in the editor below.")
    print("Press Ctrl+S when finished to send to the AI agent.")
    print("Press Ctrl+C to cancel.")
    print()

    try:
        # Launch text editor and get content
        editor = TextEditor()
        content = editor.run()

        if content is None:  # User cancelled with Ctrl+C
            print("\nCancelled by user.")
            return 0

        # If content is empty, exit gracefully
        if not content.strip():
            print("No content provided. Exiting.")
            return 0

        # Send content to agent in streaming mode
        print("\n🔄 Sending to AI agent...")

        try:
            # Get CLI instance
            cli = get_agent_cli()

            # Enable streaming mode in configuration
            session_id = uuid7()
            config = AgentConfigPresets.worker(session_id=session_id)
            config.enable_streaming = True  # Enable streaming for real-time output

            # Run with streaming display - this will use the provider-specific parser
            output, metadata = cli.run_print(
                instruction=content,
                agent_config=config,
            )

            print(f"\n✅ Session {session_id} completed")

            return 0
        except Exception as e:
            print(f"\n❌ Error during agent execution: {e}")
            return 1

    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 0
    except Exception as e:
        print(f"Error in interactive mode: {e}")
        return 1
```

### 3. Configuration Options

#### 3.1. Default Behavior Toggle

Add an option to `.env` to control whether editor mode is the default:

```bash
# Enable interactive editor as default mode for ami-agent
AMI_AGENT_DEFAULT_EDITOR_MODE=true
```

#### 3.2. Agent Configuration

The editor mode will use the same agent configuration as the `--print` mode by default, using the worker preset with hooks enabled.

### 4. User Experience Flow

1. User runs `ami-agent` (without arguments)
2. Terminal-based text editor opens with a welcome message
3. User composes their instruction/request
4. User presses `Ctrl+S` to send the content to the AI agent
5. The content is sent to the AI agent in `--print` mode
6. Agent's response is displayed in the terminal below the editor
7. User can run `ami-agent` again for another interaction

### 5. Additional Features

#### 5.1. Editor Templates

Provide template options for different types of requests:

- `ami-agent --interactive-editor --template coding` (for coding tasks)
- `ami-agent --interactive-editor --template research` (for research tasks)
- `ami-agent --interactive-editor --template documentation` (for documentation tasks)

#### 5.2. Conversation History

Consider adding a flag to include recent conversation history in the editor:
- `ami-agent --interactive-editor --with-history` to include previous exchanges

## Benefits

1. **Improved UX**: Users can compose complex instructions in a proper text editor
2. **Better Workflow**: Think-in-editor paradigm similar to email clients
3. **No Context Limits**: No need to type long instructions on the command line
4. **Paste Support**: Built-in bracketed paste mode for large content
5. **Familiar Shortcuts**: Standard text editor functionality available
6. **Streamlined Process**: Single command for the full agent interaction

## Implementation Priority

1. **Phase 1**: Basic integration (editor opens, Ctrl+S sends to agent)
2. **Phase 2**: Enhanced streaming output display 
3. **Phase 3**: Template support and conversation history
4. **Phase 4**: Optional default mode toggle

## Security Considerations

- Content from the editor passes through the same validation as `--print` mode
- No additional security risks introduced
- Existing hook validation and safety mechanisms remain intact