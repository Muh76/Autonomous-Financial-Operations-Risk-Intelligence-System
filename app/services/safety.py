from app.schemas.safety import SafetyAssessmentRequest, SafetyAssessmentResult, SafetyLevel


class SafetyService:
    async def assess(self, payload: SafetyAssessmentRequest) -> SafetyAssessmentResult:
        normalized_signal = payload.signal.lower()
        level: SafetyLevel = (
            "critical" if "critical" in normalized_signal else "high" if "urgent" in normalized_signal else "low"
        )
        action = "escalate" if level in {"high", "critical"} else "monitor"
        return SafetyAssessmentResult(subject_id=payload.subject_id, level=level, action=action)
