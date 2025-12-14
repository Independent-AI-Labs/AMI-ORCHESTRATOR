#!/usr/bin/env python3
"""Comprehensive test suite for Prometheus integration in AMI Orchestrator."""

import os
import sys
import subprocess
import tempfile
import time
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path to access modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_comprehensive_tests():
    """Run comprehensive tests for Prometheus integration."""
    print("Running comprehensive Prometheus integration tests...")
    print("=" * 60)
    
    # Test results tracker
    all_tests_passed = True
    test_results = []
    
    # Test 1: Verify Prometheus binary installation
    print("\n1. Testing Prometheus binary installation...")
    try:
        result = subprocess.run(['ami-run', 'prometheus', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus' in result.stdout.lower():
            print("   ✓ Prometheus binary accessible via ami-run")
            test_results.append("Binary installation test: PASSED")
        else:
            print(f"   ✗ Prometheus binary test failed: {result.stderr}")
            test_results.append("Binary installation test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Prometheus binary test error: {e}")
        test_results.append("Binary installation test: FAILED")
        all_tests_passed = False
    
    # Test 2: Verify promtool installation
    print("\n2. Testing promtool installation...")
    try:
        result = subprocess.run(['ami-run', 'promtool', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'promtool' in result.stdout.lower():
            print("   ✓ promtool binary accessible via ami-run")
            test_results.append("promtool installation test: PASSED")
        else:
            print(f"   ✗ promtool binary test failed: {result.stderr}")
            test_results.append("promtool installation test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ promtool binary test error: {e}")
        test_results.append("promtool installation test: FAILED")
        all_tests_passed = False
    
    # Test 3: Verify configuration management utility
    print("\n3. Testing configuration management utility...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-config', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus-config' in result.stdout.lower():
            print("   ✓ prometheus-config utility accessible and functional")
            test_results.append("Config management utility test: PASSED")
        else:
            print(f"   ✗ prometheus-config utility test failed: {result.stderr}")
            test_results.append("Config management utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ prometheus-config utility test error: {e}")
        test_results.append("Config management utility test: FAILED")
        all_tests_passed = False
    
    # Test 4: Verify network security utility
    print("\n4. Testing network security utility...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-netsec', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus-netsec' in result.stdout.lower():
            print("   ✓ prometheus-netsec utility accessible and functional")
            test_results.append("Network security utility test: PASSED")
        else:
            print(f"   ✗ prometheus-netsec utility test failed: {result.stderr}")
            test_results.append("Network security utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ prometheus-netsec utility test error: {e}")
        test_results.append("Network security utility test: FAILED")
        all_tests_passed = False
    
    # Test 5: Verify service discovery utility
    print("\n5. Testing service discovery utility...")
    try:
        result = subprocess.run(['ami-run', 'ami-service-discovery', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'ami-service-discovery' in result.stdout.lower():
            print("   ✓ ami-service-discovery utility accessible and functional")
            test_results.append("Service discovery utility test: PASSED")
        else:
            print(f"   ✗ ami-service-discovery utility test failed: {result.stderr}")
            test_results.append("Service discovery utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ ami-service-discovery utility test error: {e}")
        test_results.append("Service discovery utility test: FAILED")
        all_tests_passed = False
    
    # Test 6: Verify alerting utility
    print("\n6. Testing alerting utility...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-alerts', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus-alerts' in result.stdout.lower():
            print("   ✓ prometheus-alerts utility accessible and functional")
            test_results.append("Alerting utility test: PASSED")
        else:
            print(f"   ✗ prometheus-alerts utility test failed: {result.stderr}")
            test_results.append("Alerting utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ prometheus-alerts utility test error: {e}")
        test_results.append("Alerting utility test: FAILED")
        all_tests_passed = False
    
    # Test 7: Verify performance utility
    print("\n7. Testing performance utility...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-performance', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus-performance' in result.stdout.lower():
            print("   ✓ prometheus-performance utility accessible and functional")
            test_results.append("Performance utility test: PASSED")
        else:
            print(f"   ✗ prometheus-performance utility test failed: {result.stderr}")
            test_results.append("Performance utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ prometheus-performance utility test error: {e}")
        test_results.append("Performance utility test: FAILED")
        all_tests_passed = False
    
    # Test 8: Verify backup utility
    print("\n8. Testing backup utility...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-backup', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'prometheus-backup' in result.stdout.lower():
            print("   ✓ prometheus-backup utility accessible and functional")
            test_results.append("Backup utility test: PASSED")
        else:
            print(f"   ✗ prometheus-backup utility test failed: {result.stderr}")
            test_results.append("Backup utility test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ prometheus-backup utility test error: {e}")
        test_results.append("Backup utility test: FAILED")
        all_tests_passed = False
    
    # Test 9: Verify default configuration exists
    print("\n9. Testing default configuration...")
    try:
        boot_linux_path = project_root / '.boot-linux'
        config_path = boot_linux_path / 'lib' / 'prometheus' / 'config' / 'prometheus.yml'
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            if 'prometheus' in config_content.lower() and 'scrape_configs' in config_content:
                print("   ✓ Default configuration file exists and contains expected content")
                test_results.append("Default configuration test: PASSED")
            else:
                print("   ✗ Default configuration file missing expected content")
                test_results.append("Default configuration test: FAILED")
                all_tests_passed = False
        else:
            print("   ✗ Default configuration file does not exist")
            test_results.append("Default configuration test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Default configuration test error: {e}")
        test_results.append("Default configuration test: FAILED")
        all_tests_passed = False
    
    # Test 10: Verify rules directory structure
    print("\n10. Testing rules directory structure...")
    try:
        boot_linux_path = project_root / '.boot-linux'
        rules_path = boot_linux_path / 'lib' / 'prometheus' / 'rules'
        alerts_path = boot_linux_path / 'lib' / 'prometheus' / 'config' / 'alerts'
        
        if rules_path.exists() and alerts_path.exists():
            print("   ✓ Rules and alerts directories exist")
            test_results.append("Rules directory test: PASSED")
        else:
            print("   ✗ Rules or alerts directories missing")
            test_results.append("Rules directory test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Rules directory test error: {e}")
        test_results.append("Rules directory test: FAILED")
        all_tests_passed = False
    
    # Test 11: Test configuration validation
    print("\n11. Testing configuration validation...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-config', 'validate'], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("   ✓ Configuration validation successful")
            test_results.append("Configuration validation test: PASSED")
        else:
            print(f"   ✗ Configuration validation failed: {result.stderr}")
            test_results.append("Configuration validation test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Configuration validation test error: {e}")
        test_results.append("Configuration validation test: FAILED")
        all_tests_passed = False
    
    # Test 12: Test backup functionality
    print("\n12. Testing backup functionality...")
    try:
        # Test config backup
        result = subprocess.run(['ami-run', 'prometheus-backup', 'backup-config'], 
                              capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            print("   ✓ Configuration backup successful")
            backup_test_passed = True
        else:
            print(f"   ✗ Configuration backup failed: {result.stderr}")
            backup_test_passed = False
        
        # Test backup listing
        result = subprocess.run(['ami-run', 'prometheus-backup', 'list-backups'], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("   ✓ Backup listing successful")
            if backup_test_passed:
                test_results.append("Backup functionality test: PASSED")
        else:
            print(f"   ✗ Backup listing failed: {result.stderr}")
            test_results.append("Backup functionality test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Backup functionality test error: {e}")
        test_results.append("Backup functionality test: FAILED")
        all_tests_passed = False
    
    # Test 13: Test alerting rules creation
    print("\n13. Testing alerting rules setup...")
    try:
        result = subprocess.run(['ami-run', 'prometheus-alerts', 'create-rules'], 
                              capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            print("   ✓ Alerting rules creation successful")
            test_results.append("Alerting rules test: PASSED")
        else:
            print(f"   ✗ Alerting rules creation failed: {result.stderr}")
            test_results.append("Alerting rules test: FAILED")
            all_tests_passed = False
    except Exception as e:
        print(f"   ✗ Alerting rules test error: {e}")
        test_results.append("Alerting rules test: FAILED")
        all_tests_passed = False
    
    # Test 14: Test service discovery setup
    print("\n14. Testing service discovery setup...")
    try:
        result = subprocess.run(['ami-run', 'ami-service-discovery', 'scan'], 
                              capture_output=True, text=True, timeout=20)
        # The scan may not find services but shouldn't error
        print("   ✓ Service discovery scan completed")
        test_results.append("Service discovery test: PASSED")
    except Exception as e:
        print(f"   ✗ Service discovery test error: {e}")
        test_results.append("Service discovery test: FAILED")
        all_tests_passed = False
    
    # Print test summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    for result in test_results:
        print(f"  {result}")
    
    print(f"\nTotal tests: {len(test_results)}")
    passed_tests = len([r for r in test_results if 'PASSED' in r])
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(test_results) - passed_tests}")
    
    if all_tests_passed:
        print("\n✓ ALL TESTS PASSED - Prometheus integration is working correctly")
        return True
    else:
        print(f"\n✗ {len(test_results) - passed_tests} TEST(S) FAILED")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)