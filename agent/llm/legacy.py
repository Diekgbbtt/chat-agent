"""The open-weight LLM (Stage 3): loaded once at startup and shared by all chatrooms."""

import threading
from typing import Dict, List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class LLM:
    def __init__(self, name: str, four_bit: bool = False):
        self.tok = AutoTokenizer.from_pretrained(name)
        if four_bit:  # small local GPU
            options = {"quantization_config": BitsAndBytesConfig(load_in_4bit=True,
                                                                 bnb_4bit_compute_dtype=torch.float16)}
        else:  # Nuvolos T4: fp16 (the T4 has no bf16)
            options = {"dtype": torch.float16 if torch.cuda.is_available() else torch.float32}
        self.model = AutoModelForCausalLM.from_pretrained(name, device_map="auto", **options)
        self._lock = threading.Lock()  # one GPU: one generation at a time

    def chat(self, messages: List[Dict[str, str]], max_new_tokens: int = 200) -> str:
        """The assistant's reply to a list of {"role": ..., "content": ...} messages."""
        inputs = self.tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt",
                                              return_dict=True).to(self.model.device)
        with self._lock, torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return self.tok.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
