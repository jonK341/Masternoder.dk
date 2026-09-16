"""
Card-game engine (pure).

Shared deck primitives plus blackjack, baccarat, and video-poker (Jacks or Better)
outcome math. Cards are encoded 0..51 (rank 1..13 × suit 0..3). All functions are
side-effect free; provably-fair shuffles use the same LCG stream pattern as mines.py.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

_MASK64 = (1 << 64) - 1
SUITS = ("spades", "hearts", "diamonds", "clubs")
RANK_LABELS = {1: "A", 11: "J", 12: "Q", 13: "K"}


def _lcg_stream(seed: int):
    state = seed & _MASK64
    if state == 0:
        state = 0x9E3779B97F4A7C15
    while True:
        state = (state * 6364136223846793005 + 1442695040888963407) & _MASK64
        yield (state >> 16) / float(1 << 48)


def card_rank(card: int) -> int:
    return (int(card) % 13) + 1


def card_suit(card: int) -> int:
    return int(card) // 13


def card_label(card: int) -> str:
    r = card_rank(card)
    s = SUITS[card_suit(card)]
    return f"{RANK_LABELS.get(r, str(r))}{s[0].upper()}"


def fresh_deck() -> List[int]:
    return list(range(52))


def shuffle_deck(rand_float: float, deck: Optional[Sequence[int]] = None) -> List[int]:
    """Fisher-Yates shuffle from one provably-fair float."""
    idx = list(deck if deck is not None else fresh_deck())
    seed = int(min(max(float(rand_float), 0.0), 0.999999999) * (1 << 52))
    gen = _lcg_stream(seed)
    n = len(idx)
    for i in range(n - 1, 0, -1):
        r = next(gen)
        j = int(r * (i + 1))
        if j > i:
            j = i
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def draw_cards(deck: List[int], count: int) -> Tuple[List[int], List[int]]:
    drawn = deck[:count]
    return drawn, deck[count:]


# ---------------------------------------------------------------------------
# Blackjack
# ---------------------------------------------------------------------------

def blackjack_value(cards: Sequence[int]) -> int:
    total = 0
    aces = 0
    for c in cards:
        r = card_rank(c)
        if r == 1:
            aces += 1
            total += 11
        elif r >= 10:
            total += 10
        else:
            total += r
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards: Sequence[int]) -> bool:
    return len(cards) == 2 and blackjack_value(cards) == 21


def dealer_should_hit(cards: Sequence[int], hit_soft_17: bool = True) -> bool:
    val = blackjack_value(cards)
    if val < 17:
        return True
    if val == 17 and hit_soft_17:
        return any(card_rank(c) == 1 for c in cards) and sum(
            11 if card_rank(c) == 1 else (10 if card_rank(c) >= 10 else card_rank(c)) for c in cards
        ) == 17
    return False


def blackjack_outcome(
    player: Sequence[int],
    dealer: Sequence[int],
    *,
    blackjack_payout: float = 1.5,
    push_on_both_bj: bool = True,
) -> Tuple[str, float]:
    """Return (outcome, return_multiplier) where multiplier is total return / bet."""
    p_bj = is_blackjack(player)
    d_bj = is_blackjack(dealer)
    if p_bj and d_bj:
        return ("push" if push_on_both_bj else "loss"), 1.0
    if p_bj:
        return "win", 1.0 + float(blackjack_payout)
    if d_bj:
        return "loss", 0.0
    p_val = blackjack_value(player)
    d_val = blackjack_value(dealer)
    if p_val > 21:
        return "loss", 0.0
    if d_val > 21 or p_val > d_val:
        return "win", 2.0
    if p_val == d_val:
        return "push", 1.0
    return "loss", 0.0


# ---------------------------------------------------------------------------
# Baccarat
# ---------------------------------------------------------------------------

def baccarat_card_value(card: int) -> int:
    r = card_rank(card)
    if r >= 10:
        return 0
    return r


def baccarat_total(cards: Sequence[int]) -> int:
    return sum(baccarat_card_value(c) for c in cards) % 10


def _baccarat_draw_third(hand: Sequence[int], deck: List[int]) -> Tuple[List[int], List[int]]:
    if len(hand) >= 3 or not deck:
        return list(hand), deck
    drawn, rest = draw_cards(deck, 1)
    return list(hand) + drawn, rest


def baccarat_deal(rand_float: float) -> Dict[str, object]:
    """Standard punto banco third-card rules; returns hands + winner side."""
    deck = shuffle_deck(rand_float)
    player, deck = draw_cards(deck, 2)
    banker, deck = draw_cards(deck, 2)
    p_total = baccarat_total(player)
    b_total = baccarat_total(banker)
    natural = p_total >= 8 or b_total >= 8

    if not natural:
        player_third: Optional[int] = None
        if p_total <= 5:
            player, deck = _baccarat_draw_third(player, deck)
            player_third = player[2] if len(player) > 2 else None
            p_total = baccarat_total(player)

        if player_third is None:
            if b_total <= 5:
                banker, deck = _baccarat_draw_third(banker, deck)
        else:
            pt = baccarat_card_value(player_third)
            if b_total <= 2:
                banker, deck = _baccarat_draw_third(banker, deck)
            elif b_total == 3 and pt != 8:
                banker, deck = _baccarat_draw_third(banker, deck)
            elif b_total == 4 and pt in (2, 3, 4, 5, 6, 7):
                banker, deck = _baccarat_draw_third(banker, deck)
            elif b_total == 5 and pt in (4, 5, 6, 7):
                banker, deck = _baccarat_draw_third(banker, deck)
            elif b_total == 6 and pt in (6, 7):
                banker, deck = _baccarat_draw_third(banker, deck)

    p_total = baccarat_total(player)
    b_total = baccarat_total(banker)
    if p_total > b_total:
        winner = "player"
    elif b_total > p_total:
        winner = "banker"
    else:
        winner = "tie"
    return {
        "player": player,
        "banker": banker,
        "player_total": p_total,
        "banker_total": b_total,
        "winner": winner,
    }


def baccarat_payout(side: str, winner: str, *, banker_commission: float = 0.05) -> float:
    """Total return multiplier (stake included) for a winning bet."""
    side = side.lower()
    winner = winner.lower()
    if side != winner:
        return 0.0 if winner != "tie" else 1.0  # tie pushes player/banker bets
    if winner == "tie":
        return 9.0
    if winner == "player":
        return 2.0
    return 1.0 + (1.0 - float(banker_commission))


# ---------------------------------------------------------------------------
# Video poker — Jacks or Better
# ---------------------------------------------------------------------------

_JB_PAYTABLE = {
    "royal_flush": 250,
    "straight_flush": 50,
    "four_kind": 25,
    "full_house": 9,
    "flush": 6,
    "straight": 4,
    "three_kind": 3,
    "two_pair": 2,
    "jacks_or_better": 1,
}


def _rank_counts(cards: Sequence[int]) -> Dict[int, int]:
    counts: Dict[int, int] = {}
    for c in cards:
        r = card_rank(c)
        counts[r] = counts.get(r, 0) + 1
    return counts


def _is_flush(cards: Sequence[int]) -> bool:
    suits = {card_suit(c) for c in cards}
    return len(suits) == 1


def _is_straight(ranks: Sequence[int]) -> bool:
    rs = sorted(set(ranks))
    if len(rs) != 5:
        return False
    if rs == [1, 10, 11, 12, 13]:
        return True
    return rs[-1] - rs[0] == 4


def evaluate_video_poker(cards: Sequence[int], paytable: Optional[Dict[str, float]] = None) -> Tuple[str, float]:
    """Return (hand_name, payout_multiplier per coin)."""
    if len(cards) != 5:
        return "none", 0.0
    table = {**_JB_PAYTABLE, **(paytable or {})}
    ranks = [card_rank(c) for c in cards]
    counts = _rank_counts(cards)
    sorted_counts = sorted(counts.values(), reverse=True)
    flush = _is_flush(cards)
    straight = _is_straight(ranks)
    royal = straight and flush and 10 in ranks and 1 in ranks
    if royal:
        return "royal_flush", float(table["royal_flush"])
    if straight and flush:
        return "straight_flush", float(table["straight_flush"])
    if sorted_counts[0] == 4:
        return "four_kind", float(table["four_kind"])
    if sorted_counts[0] == 3 and sorted_counts[1] == 2:
        return "full_house", float(table["full_house"])
    if flush:
        return "flush", float(table["flush"])
    if straight:
        return "straight", float(table["straight"])
    if sorted_counts[0] == 3:
        return "three_kind", float(table["three_kind"])
    if sorted_counts[0] == 2 and sorted_counts[1] == 2:
        return "two_pair", float(table["two_pair"])
    pairs = [r for r, n in counts.items() if n == 2]
    high_pair = any(r >= 11 or r == 1 for r in pairs)
    if high_pair:
        return "jacks_or_better", float(table["jacks_or_better"])
    return "none", 0.0


def video_poker_deal(rand_float: float) -> List[int]:
    deck = shuffle_deck(rand_float)
    hand, _ = draw_cards(deck, 5)
    return hand


def video_poker_draw(
    hand: Sequence[int],
    hold: Sequence[int],
    rand_float: float,
) -> List[int]:
    """Replace non-held cards from a shuffled remainder deck."""
    hold_set = {int(i) for i in hold if 0 <= int(i) < 5}
    kept = {hand[i] for i in hold_set}
    n_draw = 5 - len(hold_set)
    remainder = [c for c in fresh_deck() if c not in kept]
    shuffled = shuffle_deck(rand_float, remainder)
    drawn, _ = draw_cards(shuffled, n_draw)
    result = list(hand)
    di = 0
    for i in range(5):
        if i not in hold_set:
            result[i] = drawn[di]
            di += 1
    return result
