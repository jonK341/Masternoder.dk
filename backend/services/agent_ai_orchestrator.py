"""
Agent AI orchestrator.
Provides a guarded, structured AI response layer for agent routes.
"""
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime

from backend.config.agent_ai_profiles import get_agent_ai_profile
from backend.services.llm_service import llm_service


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class AgentAIOrchestrator:
    """Central service that applies profile prompts and response contracts."""

    def __init__(self) -> None:
        self._enabled = _to_bool(os.environ.get("ENABLE_AGENT_AI", "true"))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._audit_file = os.path.join(base_dir, "logs", "agents", "ai_orchestrator_audit.jsonl")
        os.makedirs(os.path.dirname(self._audit_file), exist_ok=True)

    def is_enabled(self) -> bool:
        return self._enabled

    def _audit(self, profile_key: str, outcome: str, details: Optional[Dict[str, Any]] = None) -> None:
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "profile_key": profile_key,
                "outcome": outcome,
                "details": details or {},
            }
            with open(self._audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            # Auditing should never interrupt route responses.
            pass

    def _coerce_confidence(self, value: Any) -> float:
        try:
            score = float(value)
            if score < 0:
                return 0.0
            if score > 1:
                return 1.0
            return score
        except Exception:
            return 0.5

    def get_health_metrics(self, max_lines: int = 500) -> Dict[str, Any]:
        """
        Return lightweight counters from recent audit events.
        Metrics are calculated from the tail of the audit file.
        """
        counters: Dict[str, int] = {
            "total": 0,
            "success": 0,
            "llm_error": 0,
            "invalid_json_output": 0,
            "llm_unavailable": 0,
            "agent_ai_disabled": 0,
            "profile_not_found": 0,
        }
        by_profile: Dict[str, int] = {}
        recent_outcomes = []

        if not os.path.exists(self._audit_file):
            return {
                "enabled": self.is_enabled(),
                "audit_file_present": False,
                "counters": counters,
                "profile_activity": by_profile,
            }

        try:
            with open(self._audit_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            recent = lines[-max_lines:] if len(lines) > max_lines else lines

            for line in recent:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue

                outcome = str(event.get("outcome", "")).strip()
                profile_key = str(event.get("profile_key", "unknown")).strip() or "unknown"
                counters["total"] += 1
                if outcome in counters:
                    counters[outcome] += 1
                by_profile[profile_key] = by_profile.get(profile_key, 0) + 1
                recent_outcomes.append(
                    {
                        "timestamp": event.get("timestamp"),
                        "profile_key": profile_key,
                        "outcome": outcome,
                    }
                )

            success_rate = (
                round((counters["success"] / counters["total"]) * 100, 2)
                if counters["total"] > 0
                else 0.0
            )
            return {
                "enabled": self.is_enabled(),
                "audit_file_present": True,
                "sample_size": len(recent),
                "success_rate_percent": success_rate,
                "counters": counters,
                "profile_activity": by_profile,
                "last_10_outcomes": recent_outcomes[-10:],
            }
        except Exception as e:
            return {
                "enabled": self.is_enabled(),
                "audit_file_present": True,
                "error": str(e),
                "counters": counters,
                "profile_activity": by_profile,
                "last_10_outcomes": recent_outcomes[-10:],
            }

    def _sanitize_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(context, dict):
            return {}

        # Keep payload small and predictable for low-latency route responses.
        cleaned: Dict[str, Any] = {}
        for key, value in context.items():
            try:
                serialized = json.dumps(value, default=str)
                if len(serialized) > 1500:
                    cleaned[key] = serialized[:1500] + "...(truncated)"
                else:
                    cleaned[key] = value
            except Exception:
                cleaned[key] = str(value)[:400]
        return cleaned

    def _extract_json(self, content: str) -> Dict[str, Any]:
        if not content:
            return {}

        content = content.strip()
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass

        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def run_profile(
        self,
        profile_key: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile = get_agent_ai_profile(profile_key)
        if not profile:
            self._audit(profile_key, "profile_not_found")
            return {
                "used_ai": False,
                "success": False,
                "reason": "profile_not_found",
            }

        if not self.is_enabled():
            self._audit(profile_key, "agent_ai_disabled")
            return {
                "used_ai": False,
                "success": False,
                "reason": "agent_ai_disabled",
            }

        if not llm_service.is_available():
            self._audit(profile_key, "llm_unavailable")
            return {
                "used_ai": False,
                "success": False,
                "reason": "llm_unavailable",
            }

        safe_context = self._sanitize_context(context)
        system_prompt = (
            f"{profile.get('system_prompt', '')}\n\n"
            "Return only JSON with keys: intent, action, confidence, response_text, next_steps."
        )
        prompt = (
            f"Task: {user_prompt}\n"
            f"Allowed actions: {', '.join(profile.get('allowed_actions', []))}\n"
            f"Context JSON: {json.dumps(safe_context, default=str)}\n"
            "Output strict JSON only."
        )

        result = llm_service.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            model=profile.get("model"),
            temperature=profile.get("temperature", 0.2),
            max_tokens=profile.get("max_tokens", 300),
            task_type="reason",
        )

        if not result.success:
            self._audit(profile_key, "llm_error", {"error": result.error})
            return {
                "used_ai": True,
                "success": False,
                "reason": "llm_error",
                "error": result.error,
            }

        parsed = self._extract_json(result.content or "")
        if not parsed:
            self._audit(profile_key, "invalid_json_output")
            return {
                "used_ai": True,
                "success": False,
                "reason": "invalid_json_output",
                "raw_output": (result.content or "")[:600],
            }

        self._audit(
            profile_key,
            "success",
            {"model": profile.get("model"), "usage": result.usage or {}},
        )
        return {
            "used_ai": True,
            "success": True,
            "profile": profile.get("profile_name", profile_key),
            "output": {
                "intent": parsed.get("intent", "assist"),
                "action": parsed.get("action", "summarize"),
                "confidence": self._coerce_confidence(parsed.get("confidence", 0.5)),
                "response_text": parsed.get("response_text", ""),
                "next_steps": parsed.get("next_steps", []),
            },
            "usage": result.usage or {},
        }


agent_ai_orchestrator = AgentAIOrchestrator()
