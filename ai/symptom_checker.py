"""Rule-based symptom checker for safe, explainable triage support."""

import re


URGENT_KEYWORDS = {
    "chest pain",
    "breathing issue",
    "breathing issues",
    "breathing difficulty",
    "shortness of breath",
    "unconscious",
    "passed out",
    "fainted",
    "heart attack",
}

SYMPTOM_KEYWORDS = {
    "fever": ["fever", "temperature", "high temp", "hot body"],
    "headache": ["headache", "migraine", "head pain"],
    "cold": ["cold", "runny nose", "sore throat", "sneezing", "congestion", "cough", "coughing"],
    "stomach pain": ["stomach pain", "abdominal pain", "tummy pain", "stomach ache"],
}


def _extract_temperature_celsius(text):
    """Extract temperature from free text and normalize to Celsius when possible."""
    lower = text.lower()

    c_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*°?\s*c", lower)
    if c_match:
        return float(c_match.group(1))

    f_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*°?\s*f", lower)
    if f_match:
        f_val = float(f_match.group(1))
        return (f_val - 32) * 5.0 / 9.0

    # Pattern like "104 fever" often implies Fahrenheit.
    fever_num = re.search(r"\b(\d{2,3}(?:\.\d+)?)\s*(?:fever|temp|temperature)\b", lower)
    if fever_num:
        num = float(fever_num.group(1))
        if 90 <= num <= 110:
            return (num - 32) * 5.0 / 9.0
        if 35 <= num <= 45:
            return num

    # If user writes values like 38.5 without unit, assume Celsius if plausible.
    plain = re.search(r"\b(3[5-9](?:\.\d+)?)\b", lower)
    if plain:
        return float(plain.group(1))

    return None


def _extract_duration_days(text):
    """Extract rough symptom duration in days from free text."""
    lower = text.lower()
    day_match = re.search(r"for\s+(\d+)\s+day", lower)
    if day_match:
        return int(day_match.group(1))
    if "since yesterday" in lower:
        return 1
    if "few days" in lower:
        return 3
    return None


def _detect_symptom(text):
    lower = text.lower()
    for symptom, terms in SYMPTOM_KEYWORDS.items():
        if any(term in lower for term in terms):
            return symptom
    return None


def _is_urgent(text):
    lower = text.lower()
    return any(keyword in lower for keyword in URGENT_KEYWORDS)


def _fever_assessment(temp_c, duration_days):
    if temp_c is not None and temp_c > 39.4:
        return "high"
    if temp_c is not None and 38 <= temp_c <= 39.4:
        return "medium"
    if temp_c is not None and 37 <= temp_c < 38:
        return "low"
    if duration_days is not None and duration_days > 3:
        return "medium"
    return "low"


def _headache_assessment(text, duration_days):
    lower = text.lower()
    severe_markers = ["worst", "severe", "10/10", "sudden", "vision", "vomiting"]
    if any(marker in lower for marker in severe_markers):
        return "high"
    if duration_days is not None and duration_days > 2:
        return "medium"
    return "low"


def _cold_assessment(text):
    lower = text.lower()
    if "high fever" in lower or "breathing" in lower:
        return "high"
    if "persistent" in lower or "bad cough" in lower:
        return "medium"
    return "low"


def _stomach_pain_assessment(text, duration_days):
    lower = text.lower()
    if any(flag in lower for flag in ["blood", "black stool", "unbearable", "faint"]):
        return "high"
    if duration_days is not None and duration_days > 2:
        return "medium"
    return "low"


def _question_flow(symptom):
    flows = {
        "fever": [
            "What is your current temperature in Celsius or Fahrenheit?",
            "How many days has the fever lasted?",
            "Do you also have cough, sore throat, or breathing trouble?",
        ],
        "headache": [
            "When did the headache start and where is it located?",
            "How severe is it on a scale from 1 to 10?",
            "Do you have nausea, vision changes, or sensitivity to light?",
        ],
        "cold": [
            "When did your cold symptoms start?",
            "Do you have fever or breathing discomfort?",
            "Are symptoms improving, stable, or worsening?",
        ],
        "stomach pain": [
            "Where exactly is the pain and when did it start?",
            "Is the pain constant or does it come in waves?",
            "Do you have vomiting, diarrhea, fever, or blood in stool?",
        ],
    }
    return flows.get(symptom, [])


def _possible_causes(symptom):
    cause_map = {
        "fever": "a mild viral infection, inflammation, or dehydration",
        "headache": "tension, dehydration, lack of sleep, or eye strain",
        "cold": "a common viral upper respiratory infection or throat irritation",
        "stomach pain": "indigestion, food intolerance, or a mild infection",
    }
    return cause_map.get(symptom, "several possibilities that need more detail")


def _advice_for(symptom, severity):
    base = {
        "fever": "Take paracetamol if needed, stay hydrated, rest, and monitor your temperature.",
        "headache": "Hydrate, rest, and avoid screen strain when possible.",
        "cold": "Rest, keep fluids up, and monitor breathing and fever.",
        "stomach pain": "Use light meals, hydrate, and avoid trigger foods until symptoms settle.",
    }.get(symptom, "Monitor symptoms and avoid self-medicating aggressively.")

    if severity in {"medium", "high"}:
        return f"{base} Please arrange a doctor consultation soon."
    return base


def check_symptoms(user_message):
    """Return structured symptom reasoning for downstream LLM prompting."""
    urgent = _is_urgent(user_message)
    symptom = _detect_symptom(user_message)
    temp_c = _extract_temperature_celsius(user_message)
    duration_days = _extract_duration_days(user_message)
    lower = user_message.lower()

    impossible_temp = temp_c is not None and temp_c > 45
    friend_cough_context = "my friend" in lower and ("cough" in lower or "coughing" in lower)

    high_fever_phrase = any(p in lower for p in ["104 fever", "high fever"])
    fever_emergency = (temp_c is not None and temp_c >= 39.4) or high_fever_phrase

    if impossible_temp:
        return {
            "symptom": "temperature-entry",
            "severity": "low",
            "advice": "That temperature is not possible for the human body. Please check and confirm the correct value.",
            "urgent": False,
            "follow_up_questions": [
                "Could you confirm the temperature unit and value again?"
            ],
            "possible_causes": "The entered value is likely a unit or typing mistake.",
            "duration_days": duration_days,
            "temperature_c": temp_c,
            "high_fever_case": False,
            "home_care_steps": [],
            "invalid_temperature": True,
        }

    if friend_cough_context:
        return {
            "symptom": "cough",
            "severity": "low",
            "advice": "Monitor hydration, rest, and symptom progression.",
            "urgent": False,
            "follow_up_questions": [
                "Is there fever or breathing difficulty?"
            ],
            "possible_causes": "a common viral respiratory infection, throat irritation, or allergy",
            "duration_days": duration_days,
            "temperature_c": temp_c,
            "high_fever_case": False,
            "home_care_steps": ["Hydration", "Rest", "Monitor breathing"],
            "invalid_temperature": False,
            "subject": "friend",
        }

    if urgent:
        return {
            "symptom": symptom or "urgent-symptom",
            "severity": "high",
            "advice": "Immediate in-person emergency care is recommended.",
            "urgent": True,
            "follow_up_questions": [
                "Are you currently with someone who can help you seek emergency care now?"
            ],
            "possible_causes": "serious medical conditions that require urgent evaluation",
            "duration_days": duration_days,
            "temperature_c": temp_c,
            "invalid_temperature": False,
        }

    if fever_emergency:
        return {
            "symptom": "fever",
            "severity": "high",
            "advice": (
                "This is a high fever and can be dangerous. "
                "Please seek medical attention immediately."
            ),
            "urgent": True,
            "follow_up_questions": [
                "How long has this fever been present?",
                "Do you also have confusion, breathing trouble, or persistent vomiting?",
            ],
            "possible_causes": "a serious infection or significant inflammation",
            "duration_days": duration_days,
            "temperature_c": temp_c,
            "high_fever_case": True,
            "home_care_steps": [
                "Drink fluids",
                "Take paracetamol",
                "Rest",
                "Monitor temperature",
                "Seek doctor immediately",
            ],
            "invalid_temperature": False,
        }

    if not symptom:
        return {
            "symptom": None,
            "severity": "low",
            "advice": "Tell me what you are feeling, and I will guide you step by step.",
            "urgent": False,
            "follow_up_questions": [],
            "possible_causes": "not clear yet from the current message",
            "duration_days": duration_days,
            "temperature_c": temp_c,
            "invalid_temperature": False,
        }

    if symptom == "fever":
        severity = _fever_assessment(temp_c, duration_days)
    elif symptom == "headache":
        severity = _headache_assessment(user_message, duration_days)
    elif symptom == "cold":
        severity = _cold_assessment(user_message)
    else:
        severity = _stomach_pain_assessment(user_message, duration_days)

    return {
        "symptom": symptom,
        "severity": severity,
        "advice": _advice_for(symptom, severity),
        "urgent": False,
        "follow_up_questions": _question_flow(symptom)[:1],
        "possible_causes": _possible_causes(symptom),
        "duration_days": duration_days,
        "temperature_c": temp_c,
        "high_fever_case": False,
        "home_care_steps": [],
        "invalid_temperature": False,
    }
