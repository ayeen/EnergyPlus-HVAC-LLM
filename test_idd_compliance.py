#!/usr/bin/env python3
"""
Test IDD Compliance Checker

This script demonstrates the new IDD compliance checking feature.
It can check any base IDF file for IDD compliance issues and optionally auto-fix them.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.idf_handler import IDFHandler


def test_compliance_on_broken_idf():
    """Test compliance checker on the original (broken) building_with_zones.idf"""
    print("\n" + "="*70)
    print("TEST 1: Check original building_with_zones.idf (known issues)")
    print("="*70)
    
    handler = IDFHandler()
    idf_path = "data/base_idfs/building_with_zones.idf"
    
    if not os.path.exists(idf_path):
        print(f"⚠ File not found: {idf_path}")
        return
    
    idf = handler.load(idf_path)
    
    # Check without auto-fix first
    print("\n--- Without auto-fix ---")
    result = handler.check_idd_compliance(idf, auto_fix=False)
    handler.print_compliance_report(result)
    
    return result


def test_compliance_on_fixed_idf():
    """Test compliance checker on the fixed building_with_zones_fixed.idf"""
    print("\n" + "="*70)
    print("TEST 2: Check fixed building_with_zones_fixed.idf")
    print("="*70)
    
    handler = IDFHandler()
    idf_path = "data/base_idfs/building_with_zones_fixed.idf"
    
    if not os.path.exists(idf_path):
        print(f"⚠ File not found: {idf_path}")
        return
    
    idf = handler.load(idf_path)
    
    result = handler.check_idd_compliance(idf, auto_fix=False)
    handler.print_compliance_report(result)
    
    return result


def test_compliance_on_4zone():
    """Test compliance checker on 4ZoneWithShading_Simple_2.idf"""
    print("\n" + "="*70)
    print("TEST 3: Check 4ZoneWithShading_Simple_2.idf")
    print("="*70)
    
    handler = IDFHandler()
    idf_path = "data/base_idfs/4ZoneWithShading_Simple_2.idf"
    
    if not os.path.exists(idf_path):
        print(f"⚠ File not found: {idf_path}")
        return
    
    idf = handler.load(idf_path)
    
    result = handler.check_idd_compliance(idf, auto_fix=False)
    handler.print_compliance_report(result)
    
    return result


def test_auto_fix():
    """Test auto-fix capability on a copy of the broken IDF"""
    print("\n" + "="*70)
    print("TEST 4: Auto-fix demonstration")
    print("="*70)
    
    handler = IDFHandler()
    idf_path = "data/base_idfs/building_with_zones.idf"
    
    if not os.path.exists(idf_path):
        print(f"⚠ File not found: {idf_path}")
        return
    
    idf = handler.load(idf_path)
    
    print("\n--- Before auto-fix ---")
    result_before = handler.check_idd_compliance(idf, auto_fix=False)
    print(f"Compliant: {result_before['compliant']}")
    print(f"Issues: {len(result_before['issues'])}")
    
    # Now auto-fix
    print("\n--- Applying auto-fix ---")
    result_after = handler.check_idd_compliance(idf, auto_fix=True)
    
    print(f"\nFixes applied: {len(result_after['fixes_applied'])}")
    for fix in result_after['fixes_applied']:
        print(f"  🔧 {fix}")
    
    # Verify compliance after fix
    print("\n--- After auto-fix ---")
    result_verify = handler.check_idd_compliance(idf, auto_fix=False)
    print(f"Compliant: {result_verify['compliant']}")
    print(f"Remaining issues: {len([i for i in result_verify['issues'] if not i.get('fix_applied')])}")
    
    return result_after


def check_any_idf(idf_path, auto_fix=False):
    """Check any IDF file for compliance"""
    print("\n" + "="*70)
    print(f"CHECKING: {idf_path}")
    print("="*70)
    
    handler = IDFHandler()
    
    if not os.path.exists(idf_path):
        print(f"❌ File not found: {idf_path}")
        return None
    
    idf = handler.load(idf_path)
    result = handler.check_idd_compliance(idf, auto_fix=auto_fix)
    handler.print_compliance_report(result)
    
    if auto_fix and result['fixes_applied']:
        # Save fixed IDF
        output_path = idf_path.replace('.idf', '_auto_fixed.idf')
        idf.saveas(output_path)
        print(f"\n💾 Fixed IDF saved to: {output_path}")
    
    return result


def main():
    """Run all compliance tests"""
    print("\n" + "#"*70)
    print("IDD COMPLIANCE CHECKER - TEST SUITE")
    print("#"*70)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        idf_path = sys.argv[1]
        auto_fix = '--fix' in sys.argv or '-f' in sys.argv
        check_any_idf(idf_path, auto_fix=auto_fix)
        return
    
    # Run all tests
    results = {}
    
    results['broken'] = test_compliance_on_broken_idf()
    results['fixed'] = test_compliance_on_fixed_idf()
    results['4zone'] = test_compliance_on_4zone()
    results['autofix'] = test_auto_fix()
    
    # Summary
    print("\n" + "#"*70)
    print("SUMMARY")
    print("#"*70)
    
    for name, result in results.items():
        if result:
            status = "✅ COMPLIANT" if result['compliant'] else "❌ NON-COMPLIANT"
            issues = len(result['issues'])
            fixes = len(result.get('fixes_applied', []))
            print(f"  {name}: {status} ({issues} issues, {fixes} fixes)")
    
    print("\n" + "="*70)
    print("Usage: python test_idd_compliance.py [path/to/file.idf] [--fix]")
    print("  --fix or -f: Auto-fix detected issues and save to *_auto_fixed.idf")
    print("="*70)


if __name__ == "__main__":
    main()
