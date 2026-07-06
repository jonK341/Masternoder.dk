#!/usr/bin/env python3
"""
Quick script to set API keys via environment variables or command line
Usage:
    # Via environment variables:
    $env:RUNWAYML_API_KEY="key1"
    $env:PIKA_LABS_API_KEY="key2"
    python quick_set_api_keys.py

    # Or edit .env file manually
"""
import os
import sys
from pathlib import Path

def main():
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    # Create .env from .env.example if needed
    if not env_file.exists():
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print("Created .env from .env.example")
        else:
            print("Error: .env.example not found")
            return 1
    
    # Read current content
    content = env_file.read_text()
    lines = content.split('\n')
    
    # API keys from environment or command line
    api_keys = {
        'RUNWAYML_API_KEY': os.getenv('RUNWAYML_API_KEY', ''),
        'PIKA_LABS_API_KEY': os.getenv('PIKA_LABS_API_KEY', ''),
        'STABILITY_AI_API_KEY': os.getenv('STABILITY_AI_API_KEY', ''),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
    }
    
    # Also check command line args
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                if key in api_keys:
                    api_keys[key] = value
    
    updated = False
    
    # Update lines
    for i, line in enumerate(lines):
        for key, value in api_keys.items():
            if line.startswith(f'{key}=') and value:
                lines[i] = f'{key}={value}'
                print(f"✓ Updated {key}")
                updated = True
                break
    
    # Add missing keys
    existing_keys = {line.split('=')[0] for line in lines if '=' in line}
    for key, value in api_keys.items():
        if key not in existing_keys and value:
            lines.append(f'{key}={value}')
            print(f"✓ Added {key}")
            updated = True
    
    if updated:
        env_file.write_text('\n'.join(lines))
        print("\n✓ .env file updated!")
        print("\nTo deploy to server:")
        print("  python configure_api_keys.py --server")
    else:
        print("No API keys provided via environment variables or command line.")
        print("\nOptions:")
        print("  1. Set environment variables:")
        print("     $env:RUNWAYML_API_KEY='your-key'")
        print("     python quick_set_api_keys.py")
        print("  2. Use PowerShell script:")
        print("     .\\set_api_keys.ps1")
        print("  3. Edit .env file manually")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

