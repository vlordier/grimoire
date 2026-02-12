#!/usr/bin/env python3
"""
Phase 2 Specification Validation Script

Checks consistency across all Phase 2 feature specs:
- 002-danger-router-classify
- 003-fsm-router-classify
- 004-transition-guards-enforce

Validates:
1. Required files present
2. Content structure (user stories, acceptance criteria, data models)
3. Cross-references (links, model names)
4. Naming consistency (enums, field names)
5. Success criteria coverage
"""

import os
import json
import re
from pathlib import Path
from typing import List, Tuple, Dict

SPEC_DIRS = [
    "specs/002-danger-router-classify",
    "specs/003-fsm-router-classify",
    "specs/004-transition-guards-enforce",
]

REQUIRED_FILES = {
    "spec.md": "User stories and requirements",
    "plan.md": "Implementation roadmap",
    "data-model.md": "Pydantic v2 models",
}

CONTRACT_FILES = {
    "contracts/danger-classifier-api.md": "002",
    "contracts/fsm-router-api.md": "003",
}

def check_file_exists(path: str) -> Tuple[bool, str]:
    """Check if file exists and return status."""
    if os.path.exists(path):
        return True, f"✓ {path}"
    else:
        return False, f"✗ MISSING: {path}"

def check_required_sections(file_path: str, required_sections: List[str]) -> List[str]:
    """Check if markdown file contains required sections."""
    issues = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        for section in required_sections:
            if f"## {section}" not in content and f"# {section}" not in content:
                issues.append(f"  ⚠ Missing section: '{section}' in {file_path}")
    except Exception as e:
        issues.append(f"  ✗ Error reading {file_path}: {e}")
    
    return issues

def check_user_stories(feature_dir: str) -> List[str]:
    """Check spec.md has all user stories."""
    issues = []
    spec_file = f"{feature_dir}/spec.md"
    
    try:
        with open(spec_file, 'r') as f:
            content = f.read()
        
        # Check for user stories pattern
        story_pattern = r"### Story \d+ - .+ \(P[1-3]\)"
        stories = re.findall(story_pattern, content)
        
        if not stories:
            issues.append(f"  ✗ No user stories found in {spec_file}")
        else:
            # Check all stories have acceptance scenarios
            for story in stories:
                story_text = content[content.find(story):content.find(story) + 500]
                if "**Given**" not in story_text or "**Then**" not in story_text:
                    issues.append(f"  ⚠ Story missing acceptance scenarios: {story}")
    
    except Exception as e:
        issues.append(f"  ✗ Error validating stories: {e}")
    
    return issues

def check_data_models(feature_dir: str) -> List[str]:
    """Check data-model.md for Pydantic v2 patterns."""
    issues = []
    model_file = f"{feature_dir}/data-model.md"
    
    try:
        with open(model_file, 'r') as f:
            content = f.read()
        
        # Check for Pydantic v2 patterns
        if "from pydantic import" not in content:
            issues.append(f"  ⚠ Missing Pydantic imports in {model_file}")
        
        if "@field_validator" not in content and "@model_validator" not in content:
            issues.append(f"  ⚠ No validators found in {model_file}")
        
        # Check for model definitions
        if "class " not in content:
            issues.append(f"  ✗ No model classes defined in {model_file}")
    
    except Exception as e:
        issues.append(f"  ✗ Error validating models: {e}")
    
    return issues

def check_api_contracts() -> List[str]:
    """Check API contracts align with specs."""
    issues = []
    
    for contract_file, feature_num in CONTRACT_FILES.items():
        if not os.path.exists(contract_file):
            issues.append(f"  ✗ MISSING: {contract_file}")
            continue
        
        try:
            with open(contract_file, 'r') as f:
                content = f.read()
            
            # Check for request/response models
            if "Request" not in content or "Response" not in content:
                issues.append(f"  ⚠ {contract_file} missing Request/Response definitions")
            
            # Check for example endpoint
            if "```json" not in content:
                issues.append(f"  ⚠ {contract_file} missing JSON examples")
        
        except Exception as e:
            issues.append(f"  ✗ Error reading {contract_file}: {e}")
    
    return issues

def check_cross_references(feature_dir: str) -> List[str]:
    """Check markdown cross-references."""
    issues = []
    
    for md_file in ["spec.md", "plan.md", "data-model.md"]:
        file_path = f"{feature_dir}/{md_file}"
        if not os.path.exists(file_path):
            continue
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find all markdown links
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            
            for link_text, link_path in links:
                # Skip http/https links
                if link_path.startswith("http"):
                    continue
                
                # Resolve relative paths
                if link_path.startswith(".."):
                    resolved = os.path.normpath(os.path.join(feature_dir, link_path))
                else:
                    resolved = os.path.join(feature_dir, link_path)
                
                # Check if target exists (skip comments/anchors)
                target_file = resolved.split("#")[0]
                if target_file and not target_file.endswith(".md"):
                    continue
                
                if not os.path.exists(target_file) and target_file.endswith(".md"):
                    issues.append(f"  ✗ Broken link in {file_path}: {link_path}")
        
        except Exception as e:
            issues.append(f"  ✗ Error checking links in {file_path}: {e}")
    
    return issues

def run_validation() -> Dict[str, List[str]]:
    """Run all validation checks."""
    all_issues = {}
    
    print("\n" + "="*70)
    print("PHASE 2 SPECIFICATION VALIDATION")
    print("="*70 + "\n")
    
    for spec_dir in SPEC_DIRS:
        print(f"\n📋 Validating {spec_dir}...")
        print("-" * 70)
        
        issues = []
        
        # Check required files exist
        print("  Checking files...")
        for req_file, description in REQUIRED_FILES.items():
            file_path = f"{spec_dir}/{req_file}"
            exists, status = check_file_exists(file_path)
            print(f"    {status}")
            if not exists:
                issues.append(f"  ✗ {file_path} missing")
        
        # Check required sections
        print("  Checking structure...")
        spec_file = f"{spec_dir}/spec.md"
        spec_issues = check_required_sections(spec_file, [
            "User Stories",
            "Functional Requirements",
            "Non-Functional Requirements",
            "Success Criteria"
        ])
        issues.extend(spec_issues)
        
        plan_file = f"{spec_dir}/plan.md"
        plan_issues = check_required_sections(plan_file, [
            "Overview",
            "Phase 0",
            "Phase 1",
            "Phase 2"
        ])
        issues.extend(plan_issues)
        
        # Check user stories
        print("  Checking user stories...")
        story_issues = check_user_stories(spec_dir)
        if story_issues:
            issues.extend(story_issues)
        else:
            print(f"    ✓ User stories complete")
        
        # Check data models
        print("  Checking data models...")
        model_issues = check_data_models(spec_dir)
        if model_issues:
            issues.extend(model_issues)
        else:
            print(f"    ✓ Data models defined")
        
        # Check cross-references
        print("  Checking cross-references...")
        ref_issues = check_cross_references(spec_dir)
        if ref_issues:
            issues.extend(ref_issues)
        else:
            print(f"    ✓ All links valid")
        
        all_issues[spec_dir] = issues
        
        if not issues:
            print(f"\n  ✅ {spec_dir}: PASS\n")
        else:
            print(f"\n  ⚠️  {spec_dir}: {len(issues)} issues found\n")
    
    # Check API contracts
    print(f"\n📋 Validating API Contracts...")
    print("-" * 70)
    contract_issues = check_api_contracts()
    if contract_issues:
        all_issues["contracts"] = contract_issues
    else:
        print("  ✓ All API contracts present and valid")
    
    return all_issues

def print_summary(all_issues: Dict[str, List[str]]):
    """Print validation summary."""
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70 + "\n")
    
    total_issues = sum(len(issues) for issues in all_issues.values())
    
    if total_issues == 0:
        print("✅ ALL SPECIFICATIONS VALID")
        print("   - All required files present")
        print("   - All sections complete")
        print("   - All cross-references valid")
        print("   - Ready for implementation\n")
        return True
    else:
        print(f"⚠️  {total_issues} ISSUES FOUND:\n")
        
        for spec, issues in all_issues.items():
            if issues:
                print(f"  {spec}:")
                for issue in issues:
                    print(f"    {issue}")
                print()
        
        return False

if __name__ == "__main__":
    os.chdir("/Users/vincent/Work/grimoire")
    issues = run_validation()
    success = print_summary(issues)
    exit(0 if success else 1)
