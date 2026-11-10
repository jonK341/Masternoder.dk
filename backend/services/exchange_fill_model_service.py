"""Online fill-probability model for ladder rungs.

Trains a small logistic regression on completed ladder fills (label=1) versus
synthetic misses built from far levels that never filled. When fewer than
``MIN_SAMPLES`` rows exist, falls back to a distance heuristic. The model
widens ``first_bps`` / ``step_bps`` when predicted fill odds at level 0 are low.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_MODEL_PATH = os.path.join(ex._BASE, "data", "crypto_exchange", "fill_model.joblib")
_META_PATH = os.path.join(ex._BASE, "data", "crypto_exchange", "fill_model_meta.json")
_FILLS_PATH = os.path.join(ex._BASE, "logs", "cross_trade", "ladder_fills.jsonl")
MIN_SAMPLES = 12


def _features(level: int, side: str, distance_bps: float, fee_bps: float, venue: str) -> List[float]:
    return [
        float(level),
        1.0 if side == "sell" else 0.0,
        float(distance_bps),
        float(fee_bps),
        1.0 if venue == "binance" else 0.0,
    ]


def _load_fill_rows(path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = path or _FILLS_PATH
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def build_training_set(fills: Optional[List[Dict[str, Any]]] = None, *, max_level: int = 8) -> Tuple[List[List[float]], List[int]]:
    fills = fills if fills is not None else _load_fill_rows()
    X: List[List[float]] = []
    y: List[int] = []
    for row in fills:
        if row.get("kind") != "entry":
            continue
        level = int(row.get("level") or 0)
        side = str(row.get("side") or "sell")
        venue = str(row.get("venue") or "nonkyc")
        # Distance proxy: level index * 40 + 30 matches default ladder geometry.
        distance = 30.0 + level * 40.0
        fee = 10.0 if venue == "binance" else 20.0
        X.append(_features(level, side, distance, fee, venue))
        y.append(1)
        # Synthetic miss: same side one level farther.
        if level < max_level:
            X.append(_features(level + 2, side, distance + 80.0, fee, venue))
            y.append(0)
    return X, y


def train_and_save(fills: Optional[List[Dict[str, Any]]] = None, path: Optional[str] = None) -> Dict[str, Any]:
    X, y = build_training_set(fills)
    meta = {"ts": time.time(), "n": len(y), "positives": int(sum(y)), "path": path or _MODEL_PATH}
    if len(y) < MIN_SAMPLES or len(set(y)) < 2:
        meta["status"] = "heuristic"
        _save_meta(meta)
        return meta
    try:
        from sklearn.linear_model import LogisticRegression
        import joblib
    except Exception as exc:
        meta["status"] = "sklearn_unavailable"
        meta["error"] = str(exc)
        _save_meta(meta)
        return meta
    model = LogisticRegression(max_iter=200)
    model.fit(X, y)
    os.makedirs(os.path.dirname(path or _MODEL_PATH), exist_ok=True)
    import joblib
    joblib.dump(model, path or _MODEL_PATH)
    meta["status"] = "trained"
    meta["score"] = float(model.score(X, y))
    _save_meta(meta)
    return meta


def _save_meta(meta: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_META_PATH), exist_ok=True)
    with open(_META_PATH, "w", encoding="utf-8") as handle:
        json.dump(meta, handle)
        handle.write("\n")


def _load_model(path: Optional[str] = None):
    path = path or _MODEL_PATH
    if not os.path.exists(path):
        return None
    try:
        import joblib
        return joblib.load(path)
    except Exception:
        return None


def predict_fill_prob(
    *,
    level: int,
    side: str,
    distance_bps: float,
    fee_bps: float,
    venue: str,
    model_path: Optional[str] = None,
) -> float:
    model = _load_model(model_path)
    feats = _features(level, side, distance_bps, fee_bps, venue)
    if model is None:
        # Heuristic: closer + fewer fees → higher fill odds.
        return max(0.02, min(0.95, 0.85 - 0.07 * level - 0.002 * max(0.0, distance_bps - 30.0)))
    try:
        proba = model.predict_proba([feats])[0]
        # class 1 = fill
        classes = list(getattr(model, "classes_", [0, 1]))
        idx = classes.index(1) if 1 in classes else -1
        return float(proba[idx])
    except Exception:
        return max(0.02, min(0.95, 0.8 - 0.08 * level))


def tune_ladder_cfg(cfg: Dict[str, Any], *, venue: str, min_prob: float = 0.18) -> Dict[str, Any]:
    """Widen the ladder when level-0 fill odds are weak; shrink when strong."""
    out = dict(cfg)
    if not bool(cfg.get("fill_model_enabled", True)):
        out["_fill_prob_l0"] = None
        return out
    distance = float(out["first_bps"])
    p0 = predict_fill_prob(
        level=0, side="sell", distance_bps=distance, fee_bps=float(out["fee_bps"]), venue=venue,
    )
    out["_fill_prob_l0"] = round(p0, 4)
    if p0 < min_prob:
        out["first_bps"] = float(out["first_bps"]) * 0.85
        out["step_bps"] = float(out["step_bps"]) * 0.9
    elif p0 > 0.55:
        out["first_bps"] = float(out["first_bps"]) * 1.05
        out["step_bps"] = min(float(out["step_bps"]) * 1.05, float(out["first_bps"]) * 2)
    return out
