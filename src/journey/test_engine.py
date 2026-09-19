from src.journey.engine import EnergyTurnEngine

engine = EnergyTurnEngine()

result = engine.process(
    "My name is Rahul Sharma.",
    {},
)

print("ACTION:", result.action)
print("RESPONSE:", result.response)
print("EXTRACTED:", result.extracted)
print("NEXT FIELD:", result.next_field)
print("ESCALATION:", result.escalation_reason)
print("CONFIDENCE:", result.confidence)
