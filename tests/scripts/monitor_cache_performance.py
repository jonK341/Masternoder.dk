"""
Script to monitor cache hit rates and performance
"""
import sys
import time
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import module with numeric prefix using importlib
module_path = project_root / 'backend' / 'services' / '178_systems_leaderboard.py'
spec = importlib.util.spec_from_file_location('systems_178_leaderboard', module_path)
systems_178_leaderboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(systems_178_leaderboard)
leaderboard_178_systems = systems_178_leaderboard.leaderboard_178_systems


def monitor_cache_performance(iterations=10):
    """Monitor cache hit rates and performance"""
    print("=" * 60)
    print("Cache Performance Monitor")
    print("=" * 60)
    
    cache_hits = 0
    cache_misses = 0
    total_time = 0
    cached_time = 0
    uncached_time = 0
    
    test_system = 'xp'
    test_limit = 100
    
    print(f"\nTesting leaderboard: {test_system}")
    print(f"Limit: {test_limit}")
    print(f"Iterations: {iterations}\n")
    
    for i in range(iterations):
        start_time = time.time()
        result = leaderboard_178_systems.get_leaderboard(
            system_id=test_system,
            limit=test_limit,
            timeframe='all'
        )
        elapsed_ms = (time.time() - start_time) * 1000
        total_time += elapsed_ms
        
        if result.get('cached'):
            cache_hits += 1
            cached_time += elapsed_ms
            status = "✅ CACHE HIT"
        else:
            cache_misses += 1
            uncached_time += elapsed_ms
            status = "❌ CACHE MISS"
        
        print(f"Request {i+1:2d}: {status:12s} - {elapsed_ms:6.2f}ms")
    
    # Calculate statistics
    hit_rate = (cache_hits / iterations) * 100 if iterations > 0 else 0
    avg_time = total_time / iterations if iterations > 0 else 0
    avg_cached = cached_time / cache_hits if cache_hits > 0 else 0
    avg_uncached = uncached_time / cache_misses if cache_misses > 0 else 0
    
    print("\n" + "=" * 60)
    print("Performance Statistics")
    print("=" * 60)
    print(f"Cache Hit Rate:     {hit_rate:.1f}% ({cache_hits}/{iterations})")
    print(f"Cache Miss Rate:    {100-hit_rate:.1f}% ({cache_misses}/{iterations})")
    print(f"\nAverage Response Time: {avg_time:.2f}ms")
    if cache_hits > 0:
        print(f"Average (Cached):     {avg_cached:.2f}ms")
    if cache_misses > 0:
        print(f"Average (Uncached):   {avg_uncached:.2f}ms")
    
    if cache_hits > 0 and cache_misses > 0:
        speedup = avg_uncached / avg_cached if avg_cached > 0 else 0
        print(f"\nCache Speedup:        {speedup:.2f}x faster")
    
    print("=" * 60)
    
    # Recommendations
    print("\nRecommendations:")
    if hit_rate < 50:
        print("⚠️  Low cache hit rate - consider increasing TTL")
    elif hit_rate > 80:
        print("✅ Good cache hit rate")
    
    if avg_time > 100:
        print("⚠️  Response time >100ms - consider optimization")
    else:
        print("✅ Response time within target (<100ms)")


if __name__ == '__main__':
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    monitor_cache_performance(iterations)
