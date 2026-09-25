"""
Flask backend for the company study chatbot.

It exposes:
  GET  /        -> renders the chat page
  POST /chat    -> receives a user message (+ optional history),
                   asks Gemini for a reply, and returns it as JSON

The assistant's identity and behaviour rules live in chatbot_config.py.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import COMPANY_NAME, SYSTEM_PROMPT

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to your .env file before running the app."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)


def build_contents(history, message):
    """Convert chat history + the new message into Gemini's content format."""
    contents = []

    for turn in history:
        role = "model" if turn.get("role") == "assistant" else "user"
        text = str(turn.get("text", "")).strip()
        if text:
            contents.append(
                types.Content(role=role, parts=[types.Part(text=text)])
            )

    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    return contents


@app.route("/")
def index():
    return render_template("index.html", company_name=COMPANY_NAME)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_contents(history, message),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = "Sorry, I couldn't generate a response. Please try again."
    except Exception:
        return jsonify({"error": "Something went wrong while contacting the assistant."}), 500

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)
