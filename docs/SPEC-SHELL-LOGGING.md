# Shell Session Logging Specification

## Overview
This document specifies the shell session logging functionality for the AMI Orchestrator system. The system must provide immutable audit logging of all shell sessions for security and compliance purposes.

## Requirements

### 1. Auditability Requirement
- Every bash session must be logged completely and immutably
- All input and output must be captured, including prompts, commands, and results
- Logs must be tamper-proof to maintain audit integrity

### 2. Technical Requirements
- Use the `script` command to capture full terminal I/O
- Generate unique session identifiers based on timestamp, PID, and user
- Store log files in a dedicated, secure directory
- Provide optional immutability using filesystem attributes

## Implementation Details

### 1. Session Identification
Each logged session will be identified using:
- Date and time (YYYYMMDD_HHMMSS format)
- User ID (`$USER` environment variable)  
- Process ID (`$$` special variable)
- Optional UUID for additional uniqueness

Example: `session_20251125_010000_ami_12345.log`

### 2. Log File Management
- Directory: `$AMI_ROOT/logs/shell_transcripts/`
- Files created with proper permissions
- Optional immutability using `chattr +i` on Linux systems
- File naming follows consistent pattern for easy retrieval

### 3. Recursive Session Prevention
- Check for existing `SCRIPT` environment variable to prevent nested script sessions
- Use `AMI_IN_SCRIPT` flag to track whether we're already in a logged session
- Prevent infinite recursion of logging sessions

### 4. Implementation Function
```bash
ami-audit-shell() {
    # Check if already in a script session to prevent recursion
    if [[ -z "$AMI_IN_SCRIPT" ]]; then
        local log_dir="$AMI_ROOT/logs/shell_transcripts"
        mkdir -p "$log_dir"

        # Create unique session identifier
        local session_id="$(date +%Y%m%d_%H%M%S_%N)_${USER}_$$"
        local log_file="$log_dir/session_${session_id}.log"

        # Flag to prevent recursive logging
        export AMI_IN_SCRIPT=1
        export AMI_ROOT  # Preserve environment variable

        # Start logging session with proper alias support
        script -a "$log_file" -c "bash --rcfile $AMI_ROOT/scripts/setup-shell.sh -i"

        # Make log immutable after session ends (optional)
        if command -v chattr >/dev/null 2>&1; then
            chattr +i "$log_file"  # Makes file immutable (Linux)
        fi

        echo "Session logged to: $log_file"
    else
        echo "Already in a logged session"
        "$SHELL"  # Start normal shell if already logged
    fi
}
```

### 5. Direct Command Execution with Logging
To run a specific command (like `@`) with logging:
```bash
script -a "log_file.log" -c "bash --rcfile $AMI_ROOT/scripts/setup-shell.sh -i -c '@'"
```
This ensures aliases are available in the logged session.

### 6. Automatic Session Logging Setup
To enforce logging of all sessions, the `.bashrc` can be configured to automatically start all shells under `script`:
```bash
# Add to .bashrc via setup-shell.sh
if [[ -z "$AMI_IN_SCRIPT" ]]; then
    export AMI_IN_SCRIPT=1
    export AMI_ROOT
    local log_dir="$AMI_ROOT/logs/shell_transcripts"
    mkdir -p "$log_dir"
    local log_file="$log_dir/session_$(date +%Y%m%d_%H%M%S)_${USER}_$$.log"
    script -a "$log_file" -c "bash --rcfile $AMI_ROOT/scripts/setup-shell.sh -i"
    exit  # Exit original shell after script session starts
fi
```

## Security Considerations

### 1. Log Security
- Store logs in a secure directory with appropriate permissions
- Optional immutability to prevent tampering
- Secure file naming to prevent injection attacks

### 2. Environment Preservation
- Ensure all necessary environment variables are preserved in logged sessions
- Prevent loss of shell functionality due to logging wrapper

### 3. Performance Impact
- Minimal overhead for logging operations
- Efficient file I/O to prevent shell lag

## Operational Considerations

### 1. Storage Management
- Regular cleanup policies may be needed for log retention
- Monitor disk space usage for log directories
- Compression of old logs may be considered

### 2. Access Control
- Restrict access to log files to authorized personnel only
- Ensure proper permissions prevent unauthorized reading
- Audit log access itself if needed

### 3. Compliance
- Ensure logging meets organizational compliance requirements
- Maintain logs for required retention periods
- Secure deletion procedures for expired logs

## Limitations

### 1. Nested Sessions
- Prevents recursive logging with proper flags
- May interfere with some debugging workflows

### 2. Terminal Compatibility
- `script` command availability varies by system
- Some terminal features may not work identically under logging

### 3. Resource Usage
- Additional disk space for log files
- Minor performance impact for I/O operations

## Testing Requirements

### 1. Functionality Tests
- Verify all input/output is captured in logs
- Test session identification uniqueness
- Validate immutability features

### 2. Security Tests
- Verify logs are tamper-resistant
- Test recursive session prevention
- Validate environment preservation

### 3. Compatibility Tests
- Test across different terminal emulators
- Verify behavior with various shell features
- Test with different user permission levels