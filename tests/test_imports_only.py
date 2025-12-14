"""
Test import to identify where the issue occurs
"""

def test_import_only():
    """Test importing the production modules."""
    from launcher.production.deployment_strategy import DeploymentStrategy
    from launcher.production.deployment_factory import DeploymentFactory
    from launcher.production.makefile_strategy import MakefileDeploymentStrategy
    from launcher.production.python_strategy import PythonDeploymentStrategy
    from launcher.production.generic_strategy import GenericDeploymentStrategy
    from base.backend.dataops.models.security import SecurityContext
    
    # If we reach here, imports were successful
    assert DeploymentStrategy is not None
    assert DeploymentFactory is not None