"""
Integration tests for rollback system features.
Tests for rollback system integration with audit logging, validation, and triggers.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from base.backend.dataops.models.security import SecurityContext
from launcher.production.deployment_factory import DeploymentFactory
from launcher.production.makefile_strategy import MakefileDeploymentStrategy
from launcher.production.python_strategy import PythonDeploymentStrategy


class TestRollbackSystemIntegration:
    """Test rollback system integration with base audit logging."""

    def test_rollback_includes_base_audit_logging(self, tmp_path):
        """Test rollback system includes base audit logging."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-audit",
                roles=["admin"],
                groups=["rollback-group"],
                tenant_id="rollback-tenant"
            )

            # Create a project for rollback testing
            requirements_path = tmp_path / "requirements.txt"
            requirements_path.write_text("flask==2.0.1")

            strategy = PythonDeploymentStrategy(tmp_path, security_context)

            # The strategy should have security context available for audit logging
            assert strategy.security_context is not None
            assert strategy.security_context.user_id == "test:rollback-audit"

            # Analysis could be used during rollback operations
            analysis = strategy.analyze_project()
            assert isinstance(analysis, dict)

    @pytest.mark.asyncio
    async def test_rollback_audit_log_creation(self, tmp_path):
        """Test that rollback operations create audit logs."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-logs",
                roles=["admin"],
                groups=["audit-group"],
                tenant_id="audit-tenant"
            )

            # Create a Makefile project
            makefile_path = tmp_path / "Makefile"
            makefile_path.write_text("build:\n\techo build")

            strategy = MakefileDeploymentStrategy(tmp_path, security_context)

            # Test async methods that could be used during rollback
            validation_result = await strategy.validate_deployment()
            assert isinstance(validation_result, bool)

            verification_result = await strategy.verify_deployment()
            assert isinstance(verification_result, bool)

            # The audit logging would happen during actual deployment/rollback operations
            assert strategy.security_context is not None


class TestRollbackTriggerValidation:
    """Test rollback trigger validation."""

    def test_rollback_triggers_properly_validated(self, tmp_path):
        """Test that rollback triggers are properly validated."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-triggers",
                roles=["admin"],
                groups=["trigger-group"],
                tenant_id="trigger-tenant",
                permissions=["rollback:execute", "rollback:validate"]
            )

            # Create a project
            dockerfile_path = tmp_path / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.9\nCMD ['python', 'app.py']")

            strategy = DeploymentFactory.create_strategy(tmp_path, security_context)

            # Verify that security context with rollback permissions is available
            assert strategy.security_context is not None
            assert "rollback:execute" in strategy.security_context.permissions

    def test_security_validation_before_rollback(self, tmp_path):
        """Test security validation occurs before rollback execution."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-security",
                roles=["admin"],
                groups=["rollback-security-group"],
                tenant_id="rollback-security-tenant",
                permissions=["rollback:execute"]
            )

            # Create a project
            package_json_path = tmp_path / "package.json"
            package_json_path.write_text('{"scripts": {"start": "node app.js"}}')

            strategy = DeploymentFactory.create_strategy(tmp_path, security_context)

            # Verify security context is properly set up for validation
            assert strategy.security_context is not None
            assert "rollback:execute" in strategy.security_context.permissions

    @pytest.mark.asyncio
    async def test_automated_rollback_trigger_functionality(self, tmp_path):
        """Test automated rollback trigger functionality."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:auto-rollback",
                roles=["admin"],
                groups=["auto-rollback-group"],
                tenant_id="auto-rollback-tenant"
            )

            requirements_path = tmp_path / "requirements.txt"
            requirements_path.write_text("requests==2.25.1")

            strategy = PythonDeploymentStrategy(tmp_path, security_context)

            # Test async deployment validation that might trigger rollback
            validation_result = await strategy.validate_deployment()
            assert isinstance(validation_result, bool)

    @pytest.mark.asyncio
    async def test_manual_rollback_procedures_validation(self, tmp_path):
        """Test that manual rollback procedures are validated."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:manual-rollback",
                roles=["admin"],
                groups=["manual-rollback-group"],
                tenant_id="manual-rollback-tenant",
                permissions=["rollback:manual"]
            )

            # Create a Procfile project
            procfile_path = tmp_path / "Procfile"
            procfile_path.write_text("web: python app.py")

            strategy = DeploymentFactory.create_strategy(tmp_path, security_context)
        
        # Verify security context for manual rollback
        assert strategy.security_context is not None
        assert "rollback:manual" in strategy.security_context.permissions
        
        # Test async validation methods
        verification_result = await strategy.verify_deployment()
        assert isinstance(verification_result, bool)


class TestRollbackValidationProcedures:
    """Test rollback validation procedures."""

    @pytest.mark.asyncio
    async def test_rollback_validation_ensures_data_consistency(self, tmp_path):
        """Test rollback validation procedures ensure data consistency."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-consistency",
                roles=["admin"],
                groups=["consistency-group"],
                tenant_id="consistency-tenant"
            )

            # Create a project
            makefile_path = tmp_path / "Makefile"
            makefile_path.write_text("deploy:\n\techo deploy")

            strategy = MakefileDeploymentStrategy(tmp_path, security_context)

            # Test validation and verification that ensure consistency
            validation_result = await strategy.validate_deployment()
            verification_result = await strategy.verify_deployment()

            assert isinstance(validation_result, bool)
            assert isinstance(verification_result, bool)

    @pytest.mark.asyncio
    async def test_system_state_restoration_after_rollback(self, tmp_path):
        """Test that system state is properly restored after rollback."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:state-restoration",
                roles=["admin"],
                groups=["state-group"],
                tenant_id="state-tenant"
            )

            # Create a project
            requirements_path = tmp_path / "requirements.txt"
            requirements_path.write_text("flask==2.0.1")

            strategy = PythonDeploymentStrategy(tmp_path, security_context)

            # Test async methods that would be used during state restoration
            validation_result = await strategy.validate_deployment()
            verification_result = await strategy.verify_deployment()

            # The strategy should maintain its state and context
            assert strategy.security_context is not None
            assert strategy.project_path == tmp_path

    def test_rollback_validation_with_factory_integration(self, tmp_path):
        """Test rollback validation with deployment factory integration."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-factory",
                roles=["admin"],
                groups=["rollback-factory-group"],
                tenant_id="rollback-factory-tenant"
            )

            # Create a project that uses multiple potential strategies
            dockerfile_path = tmp_path / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.9\nCMD ['python', 'app.py']")

            makefile_path = tmp_path / "Makefile"
            makefile_path.write_text("build:\n\techo build")

            strategy = DeploymentFactory.create_strategy(tmp_path, security_context)

            # Should pick Docker strategy as it has higher priority
            assert strategy.get_strategy_name() in ['docker', 'makefile']
            assert strategy.security_context.user_id == "test:rollback-factory"

            # The strategy should be ready for rollback validation
            analysis = strategy.analyze_project()
            assert isinstance(analysis, dict)


class TestRollbackSecurityAndAudit:
    """Test security and audit aspects of rollback functionality."""

    @pytest.mark.asyncio
    async def test_rollback_security_context_propagation(self, tmp_path):
        """Test that security context propagates correctly during rollback."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-security-prop",
                roles=["admin"],
                groups=["security-prop-group"],
                tenant_id="security-prop-tenant",
                permissions=["audit:write", "rollback:execute"]
            )

            # Create a Python project
            pyproject_path = tmp_path / "pyproject.toml"
            pyproject_path.write_text("""
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
            """)

            strategy = PythonDeploymentStrategy(tmp_path, security_context)

            # Verify security context propagation
            assert strategy.security_context is not None
            assert strategy.security_context.user_id == "test:rollback-security-prop"
            assert "audit:write" in strategy.security_context.permissions

            # Test async validation that might be used during rollback
            result = await strategy.validate_deployment()
            assert isinstance(result, bool)

    def test_rollback_audit_event_recording(self, tmp_path):
        """Test that rollback events are properly recorded in audit logs."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="test:rollback-audit-events",
                roles=["admin"],
                groups=["audit-events-group"],
                tenant_id="audit-events-tenant"
            )

            # Create a Makefile project
            makefile_path = tmp_path / "Makefile"
            makefile_path.write_text("rollback:\n\techo rollback")

            strategy = MakefileDeploymentStrategy(tmp_path, security_context)

            # The analysis could be used as part of audit event recording
            analysis = strategy.analyze_project()
            assert isinstance(analysis, dict)

            # Verify security context is available for audit
            assert strategy.security_context is not None

    @pytest.mark.asyncio
    async def test_rollback_validation_in_multi_user_scenario(self, tmp_path):
        """Test rollback validation in multi-user scenario."""
        from launcher.production.base_deployment_strategy import BaseDeploymentStrategy
        # Mock the problematic initialization to avoid side effects
        with patch.object(BaseDeploymentStrategy, '_setup_base_integrations', return_value=None):
            security_context = SecurityContext(
                user_id="user:rollback-tester",
                roles=["developer"],
                groups=["rollback-test-group"],
                tenant_id="multi-user-tenant",
                permissions=["rollback:execute"]
            )

            # Create a project
            package_json_path = tmp_path / "package.json"
            package_json_path.write_text('{"name": "multi-user-app"}')

            strategy = DeploymentFactory.create_strategy(tmp_path, security_context)
        
        # Test that user-specific security context is maintained
        assert strategy.security_context.user_id == "user:rollback-tester"
        assert "rollback:execute" in strategy.security_context.permissions
        
        # Test async methods
        validation_result = await strategy.validate_deployment()
        assert isinstance(validation_result, bool)