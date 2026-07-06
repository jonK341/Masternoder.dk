"""
Simple script to start using the A+ Video Generation System
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def create_video(title, description="", quality="high", theme="cinematic"):
    """Create a video"""
    print(f"\n{'='*60}")
    print(f"Creating Video: {title}")
    print(f"{'='*60}")
    
    payload = {
        "title": title,
        "description": description,
        "quality": quality,
        "theme": theme,
        "category": "documentary"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/generator/create",
            json=payload,
            timeout=15
        )
        
        if response.status_code == 202:
            data = response.json()
            doc_id = data.get('documentary_id')
            print(f"[OK] Video creation started!")
            print(f"[VIDEO] Documentary ID: {doc_id}")
            print(f"[INFO] Message: {data.get('message')}")
            return doc_id
        else:
            print(f"[ERROR] Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return None

def check_progress(doc_id):
    """Check video generation progress"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/documentary/progress/{doc_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)
            
            print(f"\n[PROGRESS] {progress}% - {status}")
            
            if status == 'completed':
                print(f"[OK] Video completed!")
                if data.get('video_path'):
                    print(f"[PATH] Video Path: {data.get('video_path')}")
                if data.get('quality_score') is not None:
                    print(f"[QUALITY] Quality Score: {data.get('quality_score', 0):.3f}")
                if data.get('quality_level'):
                    print(f"[LEVEL] Quality Level: {data.get('quality_level')}")
                return True
            elif status == 'failed':
                print(f"[ERROR] Video generation failed")
                return False
            else:
                return None
        else:
            print(f"[WARN] Could not get progress (status: {response.status_code})")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error checking progress: {e}")
        return None

def main():
    """Main usage example"""
    print("\n" + "="*60)
    print("A+ Video Generation System - Usage Example")
    print("="*60)
    
    # Example 1: Create a high-quality video
    print("\n[EXAMPLE 1] Creating High Quality Video")
    doc_id = create_video(
        title="Beautiful Sunset Over Mountains",
        description="A cinematic sunset scene with dramatic clouds and mountain silhouettes",
        quality="high",
        theme="cinematic"
    )
    
    if doc_id:
        # Monitor progress
        print("\n[MONITORING] Watching progress...")
        max_checks = 30
        for i in range(max_checks):
            result = check_progress(doc_id)
            if result is True:  # Completed
                break
            elif result is False:  # Failed
                break
            time.sleep(2)
    
    # Example 2: Create ultra quality video
    print("\n\n[EXAMPLE 2] Creating Ultra Quality Video")
    doc_id2 = create_video(
        title="Ocean Waves at Dawn",
        description="4K quality footage of ocean waves at sunrise with professional cinematography",
        quality="ultra",
        theme="cinematic"
    )
    
    if doc_id2:
        print(f"\n[OK] Ultra quality video queued: {doc_id2}")
        print("[TIP] Ultra quality videos take longer but provide the best results")
    
    print("\n" + "="*60)
    print("[OK] Usage examples complete!")
    print("="*60)
    print("\n[TIPS]")
    print("  - Use 'ultra' for highest quality (longer generation time)")
    print("  - Use 'high' for good balance of quality and speed")
    print("  - Use 'medium' or 'low' for faster generation")
    print("  - Check progress with: GET /api/documentary/progress/{doc_id}")
    print("\n[API DOCS]")
    print("  POST /api/generator/create - Create video")
    print("  GET  /api/documentary/progress/{id} - Check progress")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

