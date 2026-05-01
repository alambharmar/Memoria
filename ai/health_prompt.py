"""Health-focused system prompts for the Memoria AI."""

SYSTEM_PROMPT = """You are Memoria, a smart and calm AI health assistant.

Behavior style:
- Sound natural and human, like a caring doctor in conversation.
- Keep responses clear and helpful.
- Do not use robotic phrases like "Insufficient details".
- CRITICAL: DO NOT repeat the same sentences. DO NOT loop on the same questions.

Conversation rules:
- If the user provides a very short / vague symptom (e.g. "I have a headache"), provide a brief likely cause, a simple home care step, and EXACTLY ONE follow-up question.
- If the user provides a LONG, DETAILED explanation (e.g. multiple sentences describing symptoms, duration, age, etc.), DO NOT ASK FOLLOW-UP QUESTIONS. Instead, give a comprehensive step-by-step guidance plan directly based on what they provided.
- Never ask a follow-up question if you already have enough information to give basic supportive advice.
- If the user asks for their profile details (like weight, height, gender, blood type), answer them directly using the USER HEALTH PROFILE without pivoting to ask about symptoms. 

Medical safety rules:
- Serious red-flag symptoms (chest pain, shortness of breath) require strong urgent advice to seek immediate emergency care.
- Do not invent extra symptoms, durations, or facts not provided by the user.

You are not a doctor and must avoid definitive diagnosis claims.
Add a short disclaimer only when clinically needed (urgent risk or medication guidance).
"""


def build_context_prompt(health_profile, recent_memories, symptom_context=None):
    """Build a context-aware prompt with the user's health data and memories."""
    parts = [SYSTEM_PROMPT]

    if health_profile:
        parts.append("\n--- USER HEALTH PROFILE ---")
        if health_profile.get("name"):
            parts.append(f"Name: {health_profile['name']}")
        if health_profile.get("age"):
            parts.append(f"Age: {health_profile['age']}")
        if health_profile.get("gender"):
            parts.append(f"Gender: {health_profile['gender']}")
        if health_profile.get("blood_type"):
            parts.append(f"Blood Group: {health_profile['blood_type']}")
        if health_profile.get("height"):
            parts.append(f"Height: {health_profile['height']}")
        if health_profile.get("weight"):
            parts.append(f"Weight: {health_profile['weight']}")
        if health_profile.get("conditions"):
            parts.append(f"Known conditions: {', '.join(health_profile['conditions'])}")
        if health_profile.get("medications"):
            meds = health_profile["medications"]
            med_strs = [f"{m['name']} ({m.get('dosage', 'N/A')})" for m in meds]
            parts.append(f"Current medications: {', '.join(med_strs)}")
        if health_profile.get("allergies"):
            parts.append(f"Allergies: {', '.join(health_profile['allergies'])}")
            
        recent_symptoms = health_profile.get("tracked_symptoms", [])
        if recent_symptoms:
            parts.append("\n--- RECENT LOGGED SYMPTOMS ---")
            for s in recent_symptoms[:5]:
                parts.append(f"- {s.get('symptom')} (Severity: {s.get('severity')}/10, Logged: {s.get('timestamp', '')[:10]})")
                
        recent_vitals = health_profile.get("tracked_vitals", [])
        if recent_vitals:
            parts.append("\n--- RECENT LOGGED VITALS ---")
            for v in recent_vitals[:5]:
                parts.append(f"- {v.get('type')}: {v.get('value')} {v.get('unit')} (Logged: {v.get('timestamp', '')[:10]})")

    if recent_memories:
        parts.append("\n--- RECENT CONVERSATION CONTEXT ---")
        for mem in recent_memories[-5:]:
            parts.append(f"- {mem}")

    if symptom_context:
        parts.append("\n--- SYMPTOM CHECKER CONTEXT ---")
        if symptom_context.get("symptom"):
            parts.append(f"Primary symptom: {symptom_context['symptom']}")
        parts.append(f"Rule-based severity: {symptom_context.get('severity', 'low')}")
        parts.append(f"Urgent flag: {symptom_context.get('urgent', False)}")
        if symptom_context.get("temperature_c") is not None:
            parts.append(
                f"Reported temperature (C): {symptom_context['temperature_c']:.1f}"
            )
        if symptom_context.get("duration_days") is not None:
            parts.append(f"Reported duration (days): {symptom_context['duration_days']}")
        if symptom_context.get("possible_causes"):
            parts.append(f"Possible causes framing: {symptom_context['possible_causes']}")
        if symptom_context.get("follow_up_questions"):
            parts.append("Targeted follow-up questions to ask:")
            for question in symptom_context["follow_up_questions"][:1]:
                parts.append(f"- {question}")
        if symptom_context.get("past_similar_note"):
            parts.append(f"Past pattern note: {symptom_context['past_similar_note']}")
        if symptom_context.get("high_fever_case"):
            parts.append("High fever rule triggered: urgent escalation required.")
        if symptom_context.get("home_care_steps"):
            parts.append("Required home-care steps to include:")
            for step in symptom_context["home_care_steps"]:
                parts.append(f"- {step}")

    return "\n".join(parts)
