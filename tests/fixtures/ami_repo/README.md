# ami-repo Test Fixtures

Test fixtures for ami-repo CLI comprehensive testing.

## Directory Structure

```
ami_repo/
├── test_keys/           # Pre-generated SSH keys for testing
│   ├── test_ed25519     # ED25519 private key
│   ├── test_ed25519.pub # ED25519 public key
│   ├── test_rsa         # RSA private key
│   └── test_rsa.pub     # RSA public key
└── README.md            # This file
```

## Test Keys

Pre-generated SSH keys for testing SSH authentication and access control:

- **test_ed25519**: Modern ED25519 key (recommended)
- **test_rsa**: RSA 2048-bit key (compatibility)

### Security Note

These keys are **test fixtures only** and should **never** be used for real authentication.
They are:
- Generated without passphrases for automated testing
- Committed to version control
- Publicly visible in the repository
- Used only in isolated test environments

## Usage in Tests

```python
import pytest
from pathlib import Path

@pytest.fixture
def test_ssh_key():
    """Path to test SSH public key."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "ami_repo"
    return fixtures_dir / "test_keys" / "test_ed25519.pub"
```

## Regenerating Keys

If keys need to be regenerated:

```bash
cd tests/fixtures/ami_repo/test_keys

# ED25519
ssh-keygen -t ed25519 -f test_ed25519 -N "" -C "test-ed25519-key"

# RSA
ssh-keygen -t rsa -b 2048 -f test_rsa -N "" -C "test-rsa-key"
```
