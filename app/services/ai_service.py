from groq import Groq

from app.config import get_settings


SYSTEM_PROMPT = """
You are an AI study assistant for RBI Grade B preparation.

Your job is to help the student understand concepts clearly and prepare effectively.

When study material is provided, answer the student's question using ONLY
the provided study material.

Rules:
- Can use outside knowledge when study material is provided but give priority to study material.
- Do not invent facts.
- Do not assume information that is not present in the study material.
- If the answer cannot be found in the study material, clearly say:
  "I couldn't find this information in the uploaded study material."
- Prefer clear, structured, exam-relevant explanations.
- Keep the answer concise unless the question requires more detail.
"""


class AIService:
    def __init__(self):
        settings = get_settings()
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def answer(self, question: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )

        return response.choices[0].message.content.strip()

    def answer_from_context(
        self,
        question: str,
        context: str,
    ) -> str:

        user_prompt = f"""
Study material:

{context}

Student's question:

{question}

Answer the question using only the study material above.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return response.choices[0].message.content.strip()