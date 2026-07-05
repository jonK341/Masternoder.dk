"""Setup script for real video generation integration"""
import os
import sys

def setup_api_keys():
    """Interactive script to set up API keys"""
    print("=" * 70)
    print("Real Video Generation Setup")
    print("=" * 70)
    print()
    print("This script will help you configure API keys for video generation.")
    print()
    print("You can get API keys from:")
    print("  - RunwayML: https://runwayml.com/api")
    print("  - Pika Labs: https://pika.art/api")
    print("  - Stability AI: https://platform.stability.ai/")
    print()
    
    # Check if .env file exists
    env_file = '.env'
    env_exists = os.path.exists(env_file)
    
    if env_exists:
        print(f"Found existing .env file: {env_file}")
        print("Current API keys (if any):")
        with open(env_file, 'r') as f:
            content = f.read()
            if 'RUNWAYML_API_KEY' in content:
                print("  ✅ RUNWAYML_API_KEY is set")
            if 'PIKA_LABS_API_KEY' in content:
                print("  ✅ PIKA_LABS_API_KEY is set")
            if 'STABILITY_AI_API_KEY' in content:
                print("  ✅ STABILITY_AI_API_KEY is set")
        print()
    
    print("Options:")
    print("1. Add/update API keys interactively")
    print("2. View current configuration")
    print("3. Test provider availability")
    print("4. Exit")
    print()
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == '1':
        add_api_keys(env_file)
    elif choice == '2':
        view_configuration(env_file)
    elif choice == '3':
        test_providers()
    elif choice == '4':
        print("Exiting...")
        return
    else:
        print("Invalid choice")

def add_api_keys(env_file):
    """Add or update API keys in .env file"""
    print()
    print("Enter API keys (press Enter to skip):")
    print()
    
    keys = {}
    
    runway_key = input("RunwayML API Key: ").strip()
    if runway_key:
        keys['RUNWAYML_API_KEY'] = runway_key
    
    pika_key = input("Pika Labs API Key: ").strip()
    if pika_key:
        keys['PIKA_LABS_API_KEY'] = pika_key
    
    stability_key = input("Stability AI API Key: ").strip()
    if stability_key:
        keys['STABILITY_AI_API_KEY'] = stability_key
    
    if not keys:
        print("No keys provided. Exiting...")
        return
    
    # Read existing .env file
    env_content = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Update with new keys
    env_content.update(keys)
    
    # Write back to .env
    with open(env_file, 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")
    
    print()
    print(f"✅ API keys saved to {env_file}")
    print()
    print("Next steps:")
    print("1. Restart the Flask application")
    print("2. Run: python test_provider_availability.py")
    print("3. Test video generation")

def view_configuration(env_file):
    """View current API key configuration"""
    print()
    print("Current Configuration:")
    print("-" * 70)
    
    if not os.path.exists(env_file):
        print(f"❌ {env_file} file not found")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ('API_KEY' in line or 'API' in line.upper()):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if value:
                        masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
                        print(f"  {key}: {masked}")
                    else:
                        print(f"  {key}: (empty)")

def test_providers():
    """Test provider availability"""
    print()
    print("Testing Provider Availability...")
    print("-" * 70)
    
    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not installed. Using system environment variables.")
    
    # Run the test
    try:
        from test_provider_availability import test_providers
        test_providers()
    except ImportError:
        print("Error: Could not import test_provider_availability")
        print("Make sure test_provider_availability.py is in the project root")

if __name__ == '__main__':
    try:
        setup_api_keys()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

