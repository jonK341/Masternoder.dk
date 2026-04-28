"""
Test script for middleware services
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.middleware.service_generator import generate_all_services
from backend.middleware.service_registry import middleware_service_registry

def main():
    print("=" * 70)
    print("Middleware Services Test")
    print("=" * 70)
    
    # Generate all services
    print("\n1. Generating all services...")
    count = generate_all_services()
    print(f"   ✅ Generated {count} services")
    
    # Get statistics
    print("\n2. Getting statistics...")
    stats = middleware_service_registry.get_statistics()
    print(f"   ✅ Total services: {stats['total_services']}")
    print(f"   ✅ Total connections: {stats['total_connections']}")
    print(f"   ✅ Average connections: {stats['average_connections']:.2f}")
    print(f"   ✅ Max connections per service: {stats['max_connections']}")
    
    # Show categories
    print("\n3. Service categories:")
    for category, count in stats['services_by_category'].items():
        print(f"   - {category}: {count} services")
    
    # Test a service call
    print("\n4. Testing service call...")
    try:
        result = middleware_service_registry.call_service(
            'point_calculator',
            'frontend_process_request',
            {'test': 'data'}
        )
        print(f"   ✅ Service call successful: {result}")
    except Exception as e:
        print(f"   ⚠️  Service call error: {e}")
    
    # Show top connected services
    print("\n5. Top connected services:")
    for service_id, conn_count in stats['top_connected_services'][:5]:
        print(f"   - {service_id}: {conn_count} connections")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)

if __name__ == '__main__':
    main()
