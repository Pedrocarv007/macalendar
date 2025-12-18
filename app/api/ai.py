"""AI endpoints for generating post text"""
import os
from flask import Blueprint, request, jsonify
from openai import OpenAI

ai_bp = Blueprint("ai", __name__)

# Client uses env vars: OPENAI_API_KEY, optional OPENAI_BASE_URL, OPENAI_MODEL
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada")
        base_url = os.getenv("OPENAI_BASE_URL")  # opcional (Azure ou proxy)
        _client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    return _client

@ai_bp.route("/posts", methods=["POST"])
def generate_post():
    data = request.get_json() or {}
    topic = data.get("topic") or "Promoção especial"
    tone = data.get("tone") or "informal e próximo"
    length = data.get("length") or "curto"
    language = data.get("language") or "pt-BR"

    model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    prompt = (
        "Você é um redator de social media conciso. "
        f"Escreva um post {length}, tom {tone}, em {language}, sobre: {topic}. "
        "Use call-to-action breve e hashtags moderadas."
    )

    try:
        client = get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você escreve posts curtos e claros para redes sociais."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=220,
        )
        text = resp.choices[0].message.content.strip()
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
