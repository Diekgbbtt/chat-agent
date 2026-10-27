"""Chat with the bot's LLM directly: python scripts/try_llm.py (model and 4-bit setting from .env)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import load_settings  # noqa: E402
from agent.llm import LLM  # noqa: E402

settings = load_settings()
llm = LLM(settings.llm_model, four_bit=settings.llm_4bit)

messages = [{"role": "system", "content": "You are a helpful movie assistant. Keep answers short."}]
while True:
    text = input("you> ")
    if text.strip() in ("", ":quit"):
        break
    messages.append({"role": "user", "content": text})
    reply = llm.chat(messages)
    messages.append({"role": "assistant", "content": reply})
    print("llm>", reply)
