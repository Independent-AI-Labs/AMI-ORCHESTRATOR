#!/usr/bin/env python3
"""Utility script to initialize Prometheus configuration in base storage registry."""

import sys
import os
from pathlib import Path

# Add project root to path to access base modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def initialize_prometheus_config_in_registry():
    """Initialize default Prometheus configuration in the base storage registry."""
    try:
        # Import base backend modules
        from base.backend.models.storage import StorageRegistry
        from base.scripts.env.paths import setup_imports
        
        # Setup imports for the AMI project
        setup_imports(project_root)
        
        # Connect to storage registry
        registry = StorageRegistry()
        
        # Create default Prometheus configuration
        default_config = '''# Prometheus configuration for AMI Orchestrator
# Managed by base storage registry

global:
  scrape_interval:     15s
  evaluation_interval: 15s
  # scrape_timeout is set to the global default (10s)

# Alertmanager configuration
alerting:
  alertmanagers:
  - static_configs:
    - targets:
      # - alertmanager:9093

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label 'job=<job_name>' to any timeseries scraped from this config.
  - job_name: 'prometheus'
    # Override the global default and scrape targets from this job every 5 seconds.
    scrape_interval: 5s
    static_configs:
    - targets: ['localhost:9090']

  # AMI Orchestrator services
  - job_name: 'ami-orchestrator'
    scrape_interval: 5s
    static_configs:
    - targets: ['localhost:5055']
    metrics_path: '/metrics'
  
  # Nodes production services  
  - job_name: 'nodes-production'
    scrape_interval: 10s
    static_configs:
    - targets: ['localhost:8000']  # Example node service
'''
        
        # Store the configuration in the registry
        config_path = "launcher/production/prometheus.yml"
        
        # Check if configuration already exists
        try:
            existing_config = registry.get_data(config_path)
            if existing_config:
                print(f"Prometheus configuration already exists in registry at {config_path}")
                response = input("Overwrite existing configuration? (y/N): ")
                if response.lower() != 'y':
                    print("Configuration initialization cancelled")
                    return False
        except:
            pass  # Config doesn't exist, which is fine
        
        # Store the configuration
        registry.store_data(config_path, default_config)
        print(f"Prometheus configuration initialized in registry at {config_path}")
        return True
        
    except ImportError as e:
        print(f"Base backend modules not available: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error initializing configuration in registry: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = initialize_prometheus_config_in_registry()
    sys.exit(0 if success else 1)