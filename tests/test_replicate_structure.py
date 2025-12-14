"""
Test to replicate the structure of my created tests
"""

import tempfile
from pathlib import Path

from base.backend.dataops.models.security import SecurityContext
from launcher.production.makefile_strategy import MakefileDeploymentStrategy


def test_replicate_structure():
    """Test that replicates the structure of our created tests."""
    security_context = SecurityContext(
        user_id="test:base-framework",
        roles=["admin"],
        groups=["test-group"],
        tenant_id="test-tenant"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        strategy = MakefileDeploymentStrategy(tmp_path, security_context)

        # Test that basic functionality works
        assert strategy.get_strategy_name() == "makefile"
        assert strategy.project_path == tmp_path
        assert strategy.security_context is not None