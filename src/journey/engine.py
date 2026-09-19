from src.journey.energy import ENERGY_JOURNEY
from src.journey.turn_result import TurnResult
from src.llm.client import LLMClient


class EnergyTurnEngine:
    def __init__(self):
        self.llm = LLMClient()
        self.fields = ENERGY_JOURNEY["required_fields"]

    def process(self, transcript, collected):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the decision engine for an energy customer recovery "
                    "voice agent. The journey is strictly limited to the supplied "
                    "Energy journey fields. Extract information from the customer "
                    "utterance and decide the next action.\n\n"
                    "GUARDRAILS:\n"
                    "- If the customer explicitly asks for a human, escalate.\n"
                    "- If the customer is angry, frustrated, or says stop calling, escalate "
                    "or close appropriately.\n"
                    "- Never request card, bank, payment, or other sensitive financial data.\n"
                    "- Never provide energy advice outside the supplied journey.\n"
                    "- If the customer says they are not interested or asks not to be called "
                    "again, politely close the conversation.\n"
                    "- Do not invent customer information.\n\n"
                    f"Required fields: {self.fields}\n\n"
                    "Return ONLY valid JSON with this structure:\n"
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

        raw = self.llm.chat(messages, temperature=0.0, max_tokens=400)

        import json

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return TurnResult(
                action="escalate",
                response="I will connect you with a human representative.",
                escalation_reason="Invalid decision-engine response",
                confidence=0.0,
            )

        return TurnResult(
            action=data.get("action", "escalate"),
            response=data.get("response", ""),
            extracted=data.get("extracted", {}),
            next_field=data.get("next_field"),
            escalation_reason=data.get("escalation_reason"),
            confidence=float(data.get("confidence", 0.0)),
        )
