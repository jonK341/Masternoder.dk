#!/usr/bin/env python3
"""
Simple script to set API keys in .env file
Usage: python set_env_keys.py
Then enter keys when prompted, or pass as arguments
"""
import sys
from pathlib import Path

def set_api_keys():
    """Set API keys in .env file"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    # Create .env if needed
    if not env_file.exists():
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print("Created .env from .env.example")
        else:
            print("Error: .env.example not found")
            return False
    
    # Read current content
    content = env_file.read_text()
    lines = content.split('\n')
    
    print("=" * 70)
    print("API KEY CONFIGURATION")
    print("=" * 70)
    print()
    print("Enter your API keys (press Enter to skip):")
    print()
    
    keys_config = [
        ('RUNWAYML_API_KEY', 'RunwayML API Key', 'https://runwayml.com/api'),
        ('PIKA_LABS_API_KEY', 'Pika Labs API Key', 'https://pika.art/api'),
        ('STABILITY_AI_API_KEY', 'Stability AI API Key', 'https://platform.stability.ai/'),
        ('OPENAI_API_KEY', 'OpenAI API Key', 'https://platform.openai.com/api-keys'),
    ]
    
    updated = False
    
    for key_name, display_name, url in keys_config:
        # Find current value
        current_value = None
        for i, line in enumerate(lines):
            if line.startswith(f'{key_name}='):
                current_value = line.split('=', 1)[1].strip()
                break
        
        print(f"{display_name}")
        print(f"  URL: {url}")
        if current_value:
            masked = '*' * min(len(current_value), 10) + '...' if current_value else '(not set)'
            print(f"  Current: {masked}")
        else:
            print(f"  Current: (not set)")
        
        try:
            new_value = input(f"  Enter new value (or Enter to keep current): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False
        
        if new_value:
            # Update line
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f'{key_name}='):
                    lines[i] = f'{key_name}={new_value}'
                    found = True
                    updated = True
                    break
            
            if not found:
                # Add new line
                lines.append(f'{key_name}={new_value}')
                updated = True
            
            print(f"  ✓ Updated")
        else:
            print(f"  - Skipped")
        
        print()
    
    if updated:
        # Write updated content
        env_file.write_text('\n'.join(lines))
        print("=" * 70)
        print("✓ .env file updated successfully!")
        print("=" * 70)
        print()
        print("To deploy to server, run:")
        print("  python configure_api_keys.py --server")
        return True
    else:
        print("No changes made.")
        return False

if __name__ == '__main__':
    try:
        success = set_api_keys()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)

