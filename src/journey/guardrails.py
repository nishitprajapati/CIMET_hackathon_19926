import re


def check_guardrails(transcript):
    text = transcript.lower().strip()

    # Explicitly declining further contact.
    if re.search(
        r"\b("
        r"stop calling|"
        r"don't call|"
        r"do not call|"
        r"remove me|"
        r"not interested|"
        r"do not contact me|"
        r"don't contact me|not a good time|not good time|never a good time|bad time|wrong time|can't talk|cannot talk|can't talk right now|cannot talk right now|not now|don't want to talk|do not want to talk|don't want to speak|do not want to speak"
        r")\b",
        text,
    ):
        return {
            "action": "close",
            "reason": "Customer declined further contact",
        }

    # Explicit request for a human.
    if re.search(
        r"\b("
        r"human|"
        r"agent|"
        r"representative|"
        r"real person|"
        r"speak to someone|"
        r"talk to someone|"
        r"let me speak to someone"
        r")\b",
        text,
    ):
        return {
            "action": "escalate",
            "reason": "Customer explicitly requested a human",
        }

    # Sensitive/payment information.
    if re.search(
        r"\b("
        r"card number|"
        r"credit card|"
        r"debit card|"
        r"bank account|"
        r"account number|"
        r"sort code|"
        r"cvv|"
        r"security code|"
        r"card details|"
        r"bank details"
        r")\b",
        text,
    ):
        return {
            "action": "escalate",
            "reason": "Sensitive payment information requested",
        }

    # Frustration / anger.
    if re.search(
        r"\b("
        r"angry|"
        r"furious|"
        r"frustrated|"
        r"ridiculous|"
        r"useless|"
        r"terrible service|"
        r"this is not working|"
        r"fed up|"
        r"annoyed|"
        r"waste of time|"
        r"terrible"
        r")\b",
        text,
    ):
        return {
            "action": "escalate",
            "reason": "Customer expressed frustration",
        }

    # Advice / recommendation / option-selection requests.
    # These must not be answered by the AI because the scripted
    # journey is the source of truth.
    if re.search(
        r"\b("
        r"should i|"
        r"what should i|"
        r"which one should i choose|"
        r"which should i choose|"
        r"advise me|"
        r"recommend|"
        r"what do you recommend|"
        r"what would you recommend|"
        r"what are my options|"
        r"what options do i have|"
        r"what options are there|"
        r"what options do you have|"
        r"what are the options|"
        r"can you tell me the options|"
        r"tell me the options|"
        r"what plans are available|"
        r"what plans do you have|"
        r"which plans are available|"
        r"which plans do you have|"
        r"what energy plans are available|"
        r"which energy plan should i choose|"
        r"which energy plan is best|"
        r"which plan is best|"
        r"what plan is best"
        r")\b",
        text,
    ):
        return {
            "action": "escalate",
            "reason": "Customer requested advice or plan options outside the scripted journey",
        }

    return None

