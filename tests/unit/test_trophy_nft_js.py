"""Node unit tests for the trophy NFT card helper."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NFT_JS = ROOT / "static" / "js" / "trophy-nft.js"


@pytest.fixture(scope="module")
def node_bin():
    bin_path = shutil.which("node") or shutil.which("nodejs")
    if not bin_path:
        pytest.skip("node is required to test trophy-nft.js")
    return bin_path


def _run_helper(node_bin, expression):
    script = f"""
const nft = require({json.dumps(str(NFT_JS))});
const result = {expression};
process.stdout.write(typeof result === 'string' ? result : JSON.stringify(result));
"""
    proc = subprocess.run(
        [node_bin, "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_token_ids_are_stable_and_padded(node_bin):
    collection = [
        {"id": "first_video", "name": "First Video"},
        {"id": "first_battle", "name": "First Battle"},
    ]
    expr = (
        "nft.tokenIdFromTrophy({id:'first_battle'}, "
        + json.dumps(collection)
        + ")"
    )
    assert _run_helper(node_bin, expr) == "#0002"


def test_nft_card_html_marks_minted_rarity_and_token(node_bin):
    trophy = {
        "id": "video_legend",
        "name": "Video Legend",
        "icon": "🎬",
        "category": "generation",
        "rarity": "legendary",
        "reward": 5000,
        "unlocked": True,
        "description": "Generate 100 videos",
        "requirement": "100 videos",
    }
    collection = [{"id": "first_video"}, trophy]
    expr = (
        "nft.buildNftCardHtml("
        + json.dumps(trophy)
        + ", {collection:"
        + json.dumps(collection)
        + "})"
    )
    html = _run_helper(node_bin, expr)
    assert 'class="nft-card' in html
    assert "rarity-legendary" in html
    assert "minted" in html
    assert "#0002" in html
    assert "Video Legend" in html
    assert "generation" in html
    assert "5000" in html
    assert 'data-trophy-id="video_legend"' in html


def test_nft_card_html_marks_unminted_and_escapes(node_bin):
    trophy = {
        "id": "evil<script>",
        "name": "<drop>",
        "icon": "🏆",
        "category": "special",
        "rarity": "rare",
        "reward": 10,
        "unlocked": False,
    }
    html = _run_helper(node_bin, "nft.buildNftCardHtml(" + json.dumps(trophy) + ")")
    assert "<drop>" not in html
    assert "&lt;drop&gt;" in html
    assert "unminted" in html
    assert "rarity-rare" in html
    assert "<script>" not in html
