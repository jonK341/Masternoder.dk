"""
Helper script to set up API keys for video generation providers
"""
import os
from pathlib import Path

def setup_api_keys():
    """Interactive setup for API keys"""
    print("="*70)
    print("A+ Video Generation - API Keys Setup")
    print("="*70)
    print("\nThis script helps you configure API keys for video generation providers.")
    print("You can skip any provider you don't want to use.\n")
    
    env_file = Path('.env')
    env_exists = env_file.exists()
    
    # Read existing .env if it exists
    existing_keys = {}
    if env_exists:
        print("[INFO] Found existing .env file")
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if 'API_KEY' in key or 'API' in key:
                        existing_keys[key] = value
    
    providers = {
        'RUNWAYML_API_KEY': {
            'name': 'RunwayML',
            'url': 'https://runwayml.com',
            'description': 'High-quality video generation'
        },
        'PIKA_LABS_API_KEY': {
            'name': 'Pika Labs',
            'url': 'https://pika.art',
            'description': 'AI video generation'
        },
        'STABILITY_AI_API_KEY': {
            'name': 'Stability AI (Stable Video Diffusion)',
            'url': 'https://stability.ai',
            'description': 'Stable Video Diffusion model'
        },
        'OPENAI_API_KEY': {
            'name': 'OpenAI',
            'url': 'https://platform.openai.com',
            'description': 'For script generation and content creation'
        }
    }
    
    new_keys = {}
    
    for key_name, info in providers.items():
        print(f"\n{'-'*70}")
        print(f"Provider: {info['name']}")
        print(f"URL: {info['url']}")
        print(f"Description: {info['description']}")
        
        if key_name in existing_keys:
            print(f"[INFO] Existing key found: {existing_keys[key_name][:10]}...")
            use_existing = input("Use existing key? (Y/n): ").strip().lower()
            if use_existing != 'n':
                new_keys[key_name] = existing_keys[key_name]
                continue
        
        api_key = input(f"Enter {info['name']} API key (or press Enter to skip): ").strip()
        
        if api_key:
            new_keys[key_name] = api_key
            print(f"[OK] {info['name']} API key saved")
        else:
            print(f"[SKIP] {info['name']} skipped")
    
    # Write to .env file
    print(f"\n{'-'*70}")
    print("Writing to .env file...")
    
    # Read existing .env content (excluding keys we're updating)
    env_lines = []
    if env_exists:
        with open(env_file, 'r') as f:
            for line in f:
                # Skip lines for keys we're updating
                skip = False
                for key_name in new_keys.keys():
                    if line.strip().startswith(key_name + '='):
                        skip = True
                        break
                if not skip:
                    env_lines.append(line.rstrip())
    
    # Add new/updated keys
    for key_name, value in new_keys.items():
        env_lines.append(f"{key_name}={value}")
    
    # Write to file
    with open(env_file, 'w') as f:
        for line in env_lines:
            f.write(line + '\n')
    
    print(f"[OK] API keys saved to .env file")
    print(f"\n[INFO] Configured {len(new_keys)} API key(s)")
    print("\n[NOTE] Restart Flask app for changes to take effect")
    print("="*70)

if __name__ == '__main__':
    try:
        setup_api_keys()
    except KeyboardInterrupt:
        print("\n\n[WARN] Setup cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()

