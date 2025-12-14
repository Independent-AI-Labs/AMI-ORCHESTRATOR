#!/usr/bin/env python3
"""Integration script for Prometheus with base security models in AMI Orchestrator."""

import sys
import os
from pathlib import Path
import json
import hashlib
from datetime import datetime

# Add project root to path to access base modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def integrate_with_base_security():
    """Integrate Prometheus with base security models."""
    try:
        # Import base backend security modules
        from base.backend.models.security import SecurityRegistry, AuthProvider
        from base.backend.utils.data_access import DataOpsRegistry
        from base.scripts.env.paths import setup_imports
        
        # Setup imports for the AMI project
        setup_imports(project_root)
        
        def setup_prometheus_security_integration():
            """Setup integration between Prometheus and base security models."""
            try:
                # Connect to security registry
                security_registry = SecurityRegistry()
                
                # Register Prometheus as a secured service
                service_info = {
                    "name": "prometheus",
                    "type": "monitoring",
                    "version": "2.50.1",
                    "created_at": datetime.now().isoformat(),
                    "config_path": f"{project_root}/.boot-linux/lib/prometheus/config/prometheus.yml",
                    "security_level": "high",
                    "network_policy": {
                        "allowed_cidrs": ["127.0.0.1/32"],
                        "ports": [9090],
                        "protocols": ["tcp"]
                    }
                }
                
                # Register the service in security registry
                security_registry.register_service(service_info)
                print(f"✓ Prometheus registered in base security registry")
                
                # Create security policies for Prometheus
                policy_content = {
                    "service": "prometheus",
                    "rules": [
                        {
                            "name": "localhost_only_access",
                            "description": "Allow access only from localhost",
                            "enabled": True,
                            "conditions": {
                                "source_ip_range": ["127.0.0.1/32"],
                                "destination_port": 9090
                            },
                            "action": "allow"
                        },
                        {
                            "name": "connection_limiting",
                            "description": "Limit concurrent connections",
                            "enabled": True,
                            "conditions": {
                                "max_connections": 100,
                                "time_window": 60
                            },
                            "action": "limit"
                        }
                    ]
                }
                
                # Store security policy
                policy_path = "launcher/production/prometheus-security-policy.json"
                security_registry.store_policy(policy_path, json.dumps(policy_content, indent=2))
                print(f"✓ Prometheus security policy created at {policy_path}")
                
                # Create authentication provider configuration
                auth_provider = AuthProvider()
                
                # Setup basic auth users for Prometheus web interface
                auth_config = {
                    "provider": "prometheus_basic_auth",
                    "users": [
                        {
                            "username": "admin",
                            "password_hash": hashlib.sha256("default_admin_password".encode()).hexdigest(),
                            "role": "admin",
                            "permissions": ["read", "write", "admin"]
                        },
                        {
                            "username": "monitor",
                            "password_hash": hashlib.sha256("default_monitor_password".encode()).hexdigest(),
                            "role": "viewer",
                            "permissions": ["read"]
                        }
                    ]
                }
                
                auth_provider.register_auth_config("prometheus", auth_config)
                print(f"✓ Prometheus authentication configuration registered")
                
                return True
                
            except Exception as e:
                print(f"Error setting up Prometheus security integration: {e}", file=sys.stderr)
                return False

        # Execute the security integration
        success = setup_prometheus_security_integration()
        return success
        
    except ImportError as e:
        print(f"Base backend security modules not available: {e}", file=sys.stderr)
        print("This is expected if base security modules are not yet implemented.")
        return False
    except Exception as e:
        print(f"Error integrating with base security models: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = integrate_with_base_security()
    sys.exit(0 if success else 1)