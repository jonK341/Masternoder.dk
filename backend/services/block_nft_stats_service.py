"""Backward-compat shim — use block_trophy_battle_service."""
from backend.services.block_trophy_battle_service import *  # noqa: F401,F403
from backend.services.block_trophy_battle_service import battle_with_trophy as battle_with_nft  # noqa: F401
