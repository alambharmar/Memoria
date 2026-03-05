"""Health-focused system prompts for the Memoria AI."""

SYSTEM_PROMPT = """You are Memoria, a compassionate and knowledgeable AI health assistant. \
You help users track their health, understand symptoms, manage medications, \
and maintain wellness routines.

IMPORTANT GUIDELINES:
- You are NOT a doctor. Always recommend consulting a healthcare professional for \
  medical decisions, diagnoses, or treatment plans.
- Be empathetic, supportive, and encouraging in your responses.
- When discussing symptoms, ask clarifying questions to better understand the situation.
- Provide evidence-based general health information.
- Help users track patterns in their health data over time.
- Remember past conversations and health information the user has shared.
- If a user describes an emergency situation, advise them to call emergency services \
  immediately.
- Keep responses concise but thorough.
- Use a warm, caring tone.

You have access to the user's health profile and conversation history to provide \
personalized assistance."""


def build_context_prompt(health_profile, recent_memories):
    """Build a context-aware prompt with the user's health data and memories."""
    parts = [SYSTEM_PROMPT]

    if health_profile:
        parts.append("\n--- USER HEALTH PROFILE ---")
        if health_profile.get("name"):
            parts.append(f"Name: {health_profile['name']}")
        if health_profile.get("age"):
            parts.append(f"Age: {health_profile['age']}")
        if health_profile.get("conditions"):
            parts.append(f"Known conditions: {', '.join(health_profile['conditions'])}")
        if health_profile.get("medications"):
            meds = health_profile["medications"]
            med_strs = [f"{m['name']} ({m.get('dosage', 'N/A')})" for m in meds]
            parts.append(f"Current medications: {', '.join(med_strs)}")
        if health_profile.get("allergies"):
            parts.append(f"Allergies: {', '.join(health_profile['allergies'])}")

    if recent_memories:
        parts.append("\n--- RECENT CONVERSATION CONTEXT ---")
        for mem in recent_memories[-5:]:
            parts.append(f"- {mem}")

    return "\n".join(parts)
