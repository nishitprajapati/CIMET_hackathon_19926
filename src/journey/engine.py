import json

from src.journey.energy import ENERGY_JOURNEY
from src.journey.turn_result import TurnResult
from src.journey.guardrails import check_guardrails
from src.llm.client import LLMClient


class EnergyTurnEngine:
    def __init__(self):
        self.llm = LLMClient()
        self.fields = ENERGY_JOURNEY["required_fields"]

    def process(self, transcript, collected):
        guardrail = check_guardrails(transcript)

        if guardrail:
            if guardrail["action"] == "close":
                response = "I understand. I will end the call now. Thank you and goodbye."
            else:
                response = "I understand. I will connect you with a human representative now."

            return TurnResult(
                action=guardrail["action"],
                response=response,
                extracted={},
                next_field=None,
                escalation_reason=guardrail["reason"],
                confidence=1.0,
            )

        current_missing = [
            field for field in self.fields
            if not collected.get(field)
        ]

        # The plan question is intentionally binary.
        # A clear affirmative answer means the customer wants to compare plans.
        if current_missing and current_missing[0] == "plan_interest":
            normalized = transcript.lower().strip()

            affirmative = {
                "yes",
                "yes.",
                "yeah",
                "yeah.",
                "yep",
                "yep.",
                "sure",
                "sure.",
                "absolutely",
                "absolutely.",
                "of course",
                "of course.",
                "i am",
                "i am.",
                "i'm interested",
                "i'm interested.",
                "yes i am",
                "yes i am.",
                "yeah i am",
                "yeah i am.",
            }

            if normalized in affirmative:
                updated = {
                    **collected,
                    "plan_interest": "comparing energy plans",
                }

                return TurnResult(
                    action="complete",
                    response=ENERGY_JOURNEY["completion_script"],
                    extracted={
                        "plan_interest": "comparing energy plans"
                    },
                    next_field=None,
                    escalation_reason=None,
                    confidence=1.0,
                )

            # Asking for plan options/advice is outside the scripted journey.
            option_phrases = (
                "what plans",
                "which plans",
                "what options",
                "which option",
                "what energy plans",
                "tell me the options",
                "what are the options",
                "what do you recommend",
                "which plan should",
                "what plan should",
            )

            if any(phrase in normalized for phrase in option_phrases):
                return TurnResult(
                    action="escalate",
                    response="I understand. I will connect you with a human representative who can help with the available plans.",
                    extracted={},
                    next_field=None,
                    escalation_reason="Customer requested plan options or advice outside the scripted journey",
                    confidence=1.0,
                )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are the decision engine for an energy customer recovery "
                    "voice agent. Extract journey information from the customer's "
                    "utterance and decide how to advance the journey.\n\n"

                    "The deterministic safety guardrails have already been checked.\n\n"

                    "Rules:\n"
                    "- Extract only information actually stated by the customer.\n"
                    "- Do not invent information.\n"
                    "- Do not provide energy advice.\n"
                    "- If the customer answers the current question, extract the value.\n"
                    "- If the customer has not answered, ask politely again.\n"
                    "- If the customer asks for advice, recommendations, or plan "
                    "options, escalate instead of answering.\n"
                    "- For plan_interest, the agent asks only whether the customer "
                    "is interested in comparing energy plans.\n"
                    "- A clear yes/yeah/yep/sure means plan_interest is "
                    "'comparing energy plans'.\n"
                    "- Do not invent or name energy plans.\n"
                    "- Do not treat vague statements such as 'something cheaper' "
                    "as a valid plan answer.\n\n"

                    f"Required fields: {self.fields}\n\n"

                    "Return ONLY valid JSON:\n"
                    "{"
                    '"action":"continue|escalate|close|complete",'
                    '"response":"string",'
                    '"extracted":{},'
                    '"next_field":"string or null",'
                    '"escalation_reason":"string or null",'
                    '"confidence":0.0'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Already collected: {collected}\n"
                    f"Customer said: {transcript}"
                ),
            },
        ]

        raw = self.llm.chat(
            messages,
            temperature=0.0,
            max_tokens=400,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return TurnResult(
                action="escalate",
                response="I will connect you with a human representative.",
                escalation_reason="Invalid decision-engine response",
                confidence=0.0,
            )

        extracted = data.get("extracted", {}) or {}
        updated = {**collected, **extracted}

        missing_fields = [
            field for field in self.fields
            if not updated.get(field)
        ]

        confidence = float(data.get("confidence", 0.0))

        # Low-confidence decisions must not silently continue the journey.
        if confidence < 0.5:
            return TurnResult(
                action="escalate",
                response="I want to make sure I have this right. I will connect you with a human representative.",
                extracted=extracted,
                next_field=None,
                escalation_reason="Low confidence in customer response",
                confidence=confidence,
            )

        if not missing_fields:
            return TurnResult(
                action="complete",
                response=ENERGY_JOURNEY["completion_script"],
                extracted=extracted,
                next_field=None,
                escalation_reason=None,
                confidence=confidence,
            )

        return TurnResult(
            action=data.get("action", "continue"),
            response=data.get("response", ""),
            extracted=extracted,
            next_field=missing_fields[0],
            escalation_reason=data.get("escalation_reason"),
            confidence=confidence,
        )
