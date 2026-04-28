"""Generate a video clip on production right now."""
import requests
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://masternoder.dk/vidgenerator'

print("=" * 60)
print("GENERATING VIDEO CLIP")
print("=" * 60)

r = requests.post(f'{BASE}/api/generator/create', json={
    'title': 'AI-Powered Future of Coding',
    'description': (
        'How artificial intelligence is transforming software development '
        '- from auto-complete to full autonomous agents writing, testing '
        'and deploying code. Explore neural networks that understand context, '
        'AI pair programmers, and the rise of self-healing software systems.'
    ),
    'prompt': (
        'How artificial intelligence is transforming software development '
        '- from auto-complete to full autonomous agents writing, testing '
        'and deploying code. Explore neural networks that understand context, '
        'AI pair programmers, and the rise of self-healing software systems.'
    ),
    'theme': 'technology',
    'duration': 60,
    'short_clip': True,
    'use_context': True,
    'include_points_in_clip': True,
    'generation_method': 'adaptive_ai_v2',
    'quality_mode': 'auto',
    'encode_profile': 'fast_ai',
    'ai_content': True,
    'content_category': 'technology',
    'content_context': 'AI coding, autonomous agents, software development future',
}, headers={'Content-Type': 'application/json'}, timeout=30)

d = r.json()
print(f"Status: {r.status_code}")
doc_id = d.get('documentary_id')
print(f"Video ID: {doc_id}")
print()

for i in range(30):
    time.sleep(3)
    pr = requests.get(f'{BASE}/api/documentary/progress/{doc_id}', timeout=10).json()
    status = pr.get('status', '?')
    progress = pr.get('progress', 0)
    msg = pr.get('message', '')
    print(f"  [{i+1:2d}] {status:12s} {progress:3d}% - {msg}")
    if status == 'completed':
        url = pr.get('video_url', '')
        full_url = f"https://masternoder.dk{url}"
        print()
        print("=" * 60)
        print(f"DONE! Watch your clip at:")
        print(f"  {full_url}")
        print("=" * 60)
        break
    if status == 'failed':
        err = pr.get('error_message', 'Unknown error')
        print(f"\nFAILED: {err}")
        break
else:
    print("\nTimeout after 90 seconds")
