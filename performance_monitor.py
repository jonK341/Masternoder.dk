"""
Performance Monitor - Track video generation performance
"""
import requests
import time
import json
from typing import Dict, List
from datetime import datetime
from collections import defaultdict

BASE_URL = "http://localhost:5000"

class PerformanceMonitor:
    """Monitor video generation performance"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.metrics = {
            'total_videos': 0,
            'completed': 0,
            'failed': 0,
            'average_time': 0,
            'quality_scores': [],
            'by_quality_level': defaultdict(list)
        }
    
    def monitor_video(
        self,
        doc_id: str,
        quality: str = 'unknown'
    ) -> Dict:
        """Monitor a single video generation"""
        start_time = time.time()
        status_history = []
        
        print(f"\n[MONITORING] {doc_id[:8]}... (quality: {quality})")
        
        while True:
            try:
                response = requests.get(
                    f"{self.base_url}/api/documentary/progress/{doc_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    progress = data.get('progress', 0)
                    
                    status_history.append({
                        'time': time.time() - start_time,
                        'status': status,
                        'progress': progress
                    })
                    
                    if status == 'completed':
                        elapsed = time.time() - start_time
                        quality_score = data.get('quality_score', 0.0)
                        
                        result = {
                            'doc_id': doc_id,
                            'quality': quality,
                            'status': 'completed',
                            'elapsed_time': elapsed,
                            'quality_score': quality_score,
                            'quality_level': data.get('quality_level', 'unknown'),
                            'status_history': status_history
                        }
                        
                        # Update metrics
                        self.metrics['total_videos'] += 1
                        self.metrics['completed'] += 1
                        self.metrics['quality_scores'].append(quality_score)
                        self.metrics['by_quality_level'][quality].append(elapsed)
                        
                        print(f"  [OK] Completed in {elapsed:.1f}s - Quality: {quality_score:.3f}")
                        return result
                    
                    elif status == 'failed':
                        elapsed = time.time() - start_time
                        self.metrics['total_videos'] += 1
                        self.metrics['failed'] += 1
                        
                        result = {
                            'doc_id': doc_id,
                            'quality': quality,
                            'status': 'failed',
                            'elapsed_time': elapsed,
                            'status_history': status_history
                        }
                        
                        print(f"  [FAIL] Failed after {elapsed:.1f}s")
                        return result
                
                time.sleep(2)
                
                # Timeout after 5 minutes
                if time.time() - start_time > 300:
                    print(f"  [TIMEOUT] Exceeded 5 minutes")
                    return {
                        'doc_id': doc_id,
                        'quality': quality,
                        'status': 'timeout',
                        'elapsed_time': time.time() - start_time
                    }
                    
            except Exception as e:
                print(f"  [ERROR] {e}")
                time.sleep(2)
    
    def get_statistics(self) -> Dict:
        """Get performance statistics"""
        stats = {
            'total_videos': self.metrics['total_videos'],
            'completed': self.metrics['completed'],
            'failed': self.metrics['failed'],
            'success_rate': 0.0,
            'average_time': 0.0,
            'average_quality': 0.0,
            'by_quality': {}
        }
        
        if self.metrics['total_videos'] > 0:
            stats['success_rate'] = self.metrics['completed'] / self.metrics['total_videos']
        
        # Calculate average time by quality
        for quality, times in self.metrics['by_quality_level'].items():
            if times:
                stats['by_quality'][quality] = {
                    'count': len(times),
                    'average_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
        
        # Overall average time
        all_times = []
        for times in self.metrics['by_quality_level'].values():
            all_times.extend(times)
        if all_times:
            stats['average_time'] = sum(all_times) / len(all_times)
        
        # Average quality score
        if self.metrics['quality_scores']:
            stats['average_quality'] = sum(self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
        
        return stats
    
    def print_statistics(self):
        """Print performance statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("Performance Statistics")
        print("="*70)
        
        print(f"\nOverall:")
        print(f"  Total Videos: {stats['total_videos']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Success Rate: {stats['success_rate']*100:.1f}%")
        print(f"  Average Time: {stats['average_time']:.1f}s")
        print(f"  Average Quality: {stats['average_quality']:.3f}")
        
        if stats['by_quality']:
            print(f"\nBy Quality Level:")
            for quality, data in stats['by_quality'].items():
                print(f"  {quality.upper():8s}:")
                print(f"    Count: {data['count']}")
                print(f"    Avg Time: {data['average_time']:.1f}s")
                print(f"    Min: {data['min_time']:.1f}s, Max: {data['max_time']:.1f}s")
        
        print("="*70)

def main():
    """Performance monitoring demo"""
    print("\n" + "="*70)
    print("Performance Monitor - Track Video Generation")
    print("="*70)
    
    monitor = PerformanceMonitor()
    
    # Monitor a few videos
    print("\n[INFO] This will monitor video generation performance")
    print("[INFO] Create some videos first, then enter their IDs")
    
    doc_ids = []
    print("\nEnter documentary IDs to monitor (one per line, empty to finish):")
    while True:
        doc_id = input("Doc ID: ").strip()
        if not doc_id:
            break
        quality = input("  Quality level (high/premium/ultra/etc): ").strip() or 'unknown'
        doc_ids.append((doc_id, quality))
    
    if not doc_ids:
        print("[INFO] No videos to monitor")
        return
    
    # Monitor all
    results = []
    for doc_id, quality in doc_ids:
        result = monitor.monitor_video(doc_id, quality)
        results.append(result)
        time.sleep(1)  # Brief pause between monitors
    
    # Print statistics
    monitor.print_statistics()
    
    # Save results
    results_file = "performance_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'results': results,
            'statistics': monitor.get_statistics(),
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n[INFO] Results saved to {results_file}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

