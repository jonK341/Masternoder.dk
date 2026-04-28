#!/usr/bin/env python3
"""
Test script for complete generator process workflow
Tests video creation, progress polling, and completion
"""
import sys
import requests
import json
import time

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'

def test_generator_process():
    """Test the complete generator process"""
    print("="*80)
    print("GENERATOR PROCESS TEST")
    print("="*80)
    
    # Step 1: Create a video
    print("\n[STEP 1] Creating video...")
    video_data = {
        "title": "Machine Learning Fundamentals",
        "description": "An introduction to machine learning covering supervised learning, neural networks, deep learning architectures and practical AI applications in modern software development",
        "prompt": "An introduction to machine learning covering supervised learning, neural networks, deep learning architectures and practical AI applications in modern software development",
        "theme": "technology",
        "duration": 60,
        "short_clip": True,
        "use_context": True,
        "include_points_in_clip": True,
        "generation_method": "adaptive_ai_v2",
        "quality_mode": "auto",
        "encode_profile": "fast_ai",
        "ai_content": True,
        "content_category": "technology",
        "content_context": "Machine learning, neural networks, AI applications"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/generator/create",
            json=video_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code not in [200, 201, 202]:
            print(f"❌ FAILED - Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if not data.get('success'):
            print(f"❌ FAILED - API returned success=false")
            return False
        
        doc_id = data.get('documentary_id')
        if not doc_id:
            print(f"❌ FAILED - No documentary_id in response")
            return False
        
        print(f"✅ Video created - Documentary ID: {doc_id}")
        
        # Step 2: Poll progress
        print(f"\n[STEP 2] Polling progress for {doc_id}...")
        max_polls = 30
        poll_count = 0
        
        while poll_count < max_polls:
            poll_count += 1
            print(f"\n[POLL {poll_count}/{max_polls}] Checking progress...")
            
            try:
                progress_response = requests.get(
                    f"{BASE_URL}/api/documentary/progress/{doc_id}",
                    timeout=10
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    status = progress_data.get('status', 'unknown')
                    progress = progress_data.get('progress', 0)
                    message = progress_data.get('message', '')
                    
                    print(f"  Status: {status}")
                    print(f"  Progress: {progress}%")
                    if message:
                        print(f"  Message: {message}")
                    
                    if status == 'completed':
                        print(f"\n✅ SUCCESS - Video generation completed!")
                        if progress_data.get('video_path'):
                            print(f"  Video Path: {progress_data.get('video_path')}")
                        if progress_data.get('video_url'):
                            print(f"  Video URL: {progress_data.get('video_url')}")
                        return True
                    elif status == 'failed':
                        print(f"\n❌ FAILED - Video generation failed")
                        print(f"  Error: {progress_data.get('error', 'Unknown error')}")
                        return False
                    elif status in ['queued', 'generating', 'processing']:
                        print(f"  ⏳ Still processing... waiting 3 seconds...")
                        time.sleep(3)
                    else:
                        print(f"  ⏳ Status: {status}... waiting 3 seconds...")
                        time.sleep(3)
                elif progress_response.status_code == 404:
                    if poll_count < 5:
                        print(f"  ⏳ Documentary not found yet (might be initializing)... waiting 2 seconds...")
                        time.sleep(2)
                    else:
                        print(f"  ❌ FAILED - Documentary not found after {poll_count} attempts")
                        return False
                else:
                    print(f"  ⚠️  Unexpected status: {progress_response.status_code}")
                    print(f"  Response: {progress_response.text[:200]}")
                    time.sleep(3)
                    
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Error polling progress: {e}")
                time.sleep(3)
        
        print(f"\n⚠️  TIMEOUT - Max polls reached ({max_polls})")
        print(f"  Final status check...")
        try:
            final_response = requests.get(
                f"{BASE_URL}/api/documentary/progress/{doc_id}",
                timeout=10
            )
            if final_response.status_code == 200:
                final_data = final_response.json()
                print(f"  Final Status: {final_data.get('status')}")
                print(f"  Final Progress: {final_data.get('progress', 0)}%")
        except:
            pass
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_generator_process()
    sys.exit(0 if success else 1)

