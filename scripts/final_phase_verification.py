"""
Final Phase Verification Script
Verifies all systems are ready for production launch
"""
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_services():
    """Verify all services can be imported"""
    print("Verifying Services...")
    services = [
        'backend.services.ai_agent_class',
        'backend.services.ai_skill_implementations',
        'backend.services.ceo_agent',
        'backend.services.agent_ai_intelligence',
        'backend.services.system_skills_definition',
        'backend.services.ai_content_generator',
        'backend.services.ai_power_controller'
    ]
    
    results = {}
    for service in services:
        try:
            __import__(service)
            results[service] = '[OK] OK'
            print(f"  [OK] {service}")
        except Exception as e:
            results[service] = f'[ERROR] ERROR: {str(e)}'
            print(f"  [ERROR] {service}: {e}")
    
    return results

def verify_routes():
    """Verify all routes can be imported"""
    print("\nVerifying Routes...")
    routes = [
        'backend.routes.ai_agent_routes',
        'backend.routes.ai_skill_routes',
        'backend.routes.ceo_agent_routes',
        'backend.routes.debugger_agent_routes',
        'backend.routes.debugging_master_routes'
    ]
    
    results = {}
    for route in routes:
        try:
            __import__(route)
            results[route] = '[OK] OK'
            print(f"  [OK] {route}")
        except Exception as e:
            results[route] = f'[ERROR] ERROR: {str(e)}'
            print(f"  [ERROR] {route}: {e}")
    
    return results

def verify_skills():
    """Verify all skills are implemented"""
    print("\nVerifying Skills...")
    try:
        from backend.services.system_skills_definition import system_skills_definition
        
        skills = system_skills_definition.skills
        skill_lines = skills.get('skill_lines', {})
        
        total_skills = 0
        placeholder_skills = 0
        
        for line_name, line_data in skill_lines.items():
            for skill in line_data.get('skills', []):
                total_skills += 1
                if skill.get('placeholder', False):
                    placeholder_skills += 1
                    print(f"  [WARN] Placeholder: {skill['name']}")
        
        implemented_skills = total_skills - placeholder_skills
        
        print(f"\n  Total Skills: {total_skills}")
        print(f"  [OK] Implemented: {implemented_skills}")
        print(f"  [WARN] Placeholders: {placeholder_skills}")
        
        return {
            'total': total_skills,
            'implemented': implemented_skills,
            'placeholders': placeholder_skills
        }
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {'error': str(e)}

def verify_documentation():
    """Verify all documentation exists"""
    print("\nVerifying Documentation...")
    docs = [
        'docs/FINAL_CONCLUSION.md',
        'docs/PLAN_COMPLETE.md',
        'docs/AI_ENHANCEMENT_COMPLETE.md',
        'docs/COMPLETE_SYSTEM_SUMMARY.md',
        'README_FINAL.md'
    ]
    
    results = {}
    for doc in docs:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), doc)
        if os.path.exists(path):
            size = os.path.getsize(path)
            results[doc] = f'[OK] OK ({size} bytes)'
            print(f"  [OK] {doc} ({size} bytes)")
        else:
            results[doc] = '[ERROR] MISSING'
            print(f"  [ERROR] {doc} - MISSING")
    
    return results

def generate_report():
    """Generate final verification report"""
    print("\n" + "="*60)
    print("FINAL PHASE VERIFICATION REPORT")
    print("="*60)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'services': verify_services(),
        'routes': verify_routes(),
        'skills': verify_skills(),
        'documentation': verify_documentation()
    }
    
    # Calculate overall status
    all_ok = True
    for section in ['services', 'routes', 'documentation']:
        for item, status in report[section].items():
            if '[ERROR]' in status or 'ERROR' in status:
                all_ok = False
                break
    
    if report['skills'].get('placeholders', 0) > 0:
        all_ok = False
    
    report['overall_status'] = '[OK] READY' if all_ok else '[WARN] NEEDS ATTENTION'
    
    print("\n" + "="*60)
    print(f"OVERALL STATUS: {report['overall_status']}")
    print("="*60)
    
    # Save report
    report_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'logs',
        'final_phase',
        f'verification_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nReport saved to: {report_file}")
    
    return report

if __name__ == '__main__':
    report = generate_report()
    sys.exit(0 if '[OK] READY' in report['overall_status'] else 1)
