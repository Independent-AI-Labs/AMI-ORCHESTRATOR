#!/usr/bin/env python3
"""Setup script to configure Prometheus metric collection from AMI services."""

import sys
import os
from pathlib import Path
import json

# Add project root to path to access base modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_ami_metric_collection():
    """Setup metric collection from AMI services."""
    try:
        # Define Prometheus configuration directory
        prometheus_config_dir = project_root / ".boot-linux" / "lib" / "prometheus" / "config"
        metrics_collection_dir = prometheus_config_dir / "ami-metrics"
        metrics_collection_dir.mkdir(exist_ok=True, parents=True)
        
        # Create metric collection configuration for different AMI modules
        metric_configs = {
            "ami-orchestrator": {
                "job_name": "ami-orchestrator",
                "scrape_interval": "5s",
                "scrape_timeout": "3s",
                "metrics_path": "/metrics",
                "static_configs": [
                    {
                        "targets": ["localhost:5055"],
                        "labels": {
                            "service": "ami-orchestrator",
                            "module": "orchestrator"
                        }
                    }
                ],
                "relabel_configs": [
                    {
                        "source_labels": ["__address__"],
                        "target_label": "instance",
                        "regex": "(.+)",
                        "replacement": "${1}"
                    }
                ]
            },
            "nodes-production": {
                "job_name": "nodes-production",
                "scrape_interval": "10s",
                "scrape_timeout": "5s", 
                "metrics_path": "/metrics",
                "static_configs": [
                    {
                        "targets": ["localhost:8000"],
                        "labels": {
                            "service": "nodes-production", 
                            "module": "nodes"
                        }
                    }
                ],
                "relabel_configs": [
                    {
                        "source_labels": ["__address__"],
                        "target_label": "instance",
                        "regex": "(.+)",
                        "replacement": "${1}"
                    }
                ]
            }
        }
        
        # Write the metric collection configurations to files
        for service_name, config in metric_configs.items():
            config_file = metrics_collection_dir / f"{service_name}-metrics.yml"
            with open(config_file, 'w') as f:
                # Write as YAML format for Prometheus
                f.write(f"- job_name: '{config['job_name']}'\n")
                f.write(f"  scrape_interval: {config['scrape_interval']}\n") 
                f.write(f"  scrape_timeout: {config['scrape_timeout']}\n")
                f.write(f"  metrics_path: '{config['metrics_path']}'\n")
                f.write("  static_configs:\n")
                for static_config in config['static_configs']:
                    f.write("  - targets:\n")
                    for target in static_config['targets']:
                        f.write(f"    - '{target}'\n")
                    if 'labels' in static_config:
                        f.write("    labels:\n")
                        for label_key, label_value in static_config['labels'].items():
                            f.write(f"      {label_key}: '{label_value}'\n")
                
                if 'relabel_configs' in config:
                    f.write("  relabel_configs:\n")
                    for relabel in config['relabel_configs']:
                        f.write("  - source_labels:\n")
                        for label in relabel['source_labels']:
                            f.write(f"    - '{label}'\n")
                        f.write(f"    target_label: '{relabel['target_label']}'\n")
                        f.write(f"    regex: '{relabel['regex']}'\n")
                        f.write(f"    replacement: '{relabel['replacement']}'\n")
            
            print(f"✓ Created metric collection configuration for {service_name}: {config_file}")
        
        # Create a main configuration file that includes the metric collection configs
        main_config = prometheus_config_dir / "prometheus.yml"
        if main_config.exists():
            # Append file_sd_configs to the main config to include metric collection configs
            with open(main_config, 'a') as f:
                f.write("\n# AMI Service Metric Collection\n")
                f.write("  # Additional configurations for AMI services\n") 
                f.write(f"  - job_name: 'ami-service-metrics'\n")
                f.write("    file_sd_configs:\n")
                f.write(f"      - files:\n")
                for service_name in metric_configs.keys():
                    f.write(f"        - 'ami-metrics/{service_name}-metrics.yml'\n")
                f.write("    refresh_interval: 1m\n")
            
            print(f"✓ Updated main Prometheus configuration to include metric collection")
        else:
            print("Main Prometheus configuration not found")
        
        # Create a metrics collection guide
        guide_file = metrics_collection_dir / "metrics-collection-guide.md"
        with open(guide_file, 'w') as f:
            f.write("# AMI Services Metrics Collection Guide\n\n")
            f.write("This directory contains configurations for collecting metrics from AMI services.\n\n")
            f.write("## Current Services Monitored\n\n")
            for service_name in metric_configs.keys():
                f.write(f"- {service_name}\n")
            
            f.write("\n## Configuration Files\n\n")
            f.write("Each service has its own configuration file in this directory:\n\n")
            for service_name in metric_configs.keys():
                f.write(f"- `{service_name}-metrics.yml` - Configuration for {service_name}\n")
            
            f.write("\n## Adding New Services\n\n")
            f.write("To add metric collection for a new service:\n\n")
            f.write("1. Create a new configuration file in this directory\n")
            f.write("2. Update your service to expose Prometheus metrics at `/metrics` endpoint\n")
            f.write("3. Make sure your service is running on localhost with an accessible port\n")
            f.write("4. Reload Prometheus configuration: `curl -X POST http://localhost:9090/-/reload`\n")
        
        print(f"✓ Created metrics collection guide: {guide_file}")
        
        return True
    
    except Exception as e:
        print(f"Error setting up AMI metric collection: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = setup_ami_metric_collection()
    sys.exit(0 if success else 1)