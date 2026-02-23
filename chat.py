#!/usr/bin/env python3
"""
RESON chat app su Gradio con memoria conversazionale.

Configurazione via variabili ambiente:
- MODEL_REPO: repo Hugging Face del modello fine-tuned/adapter
- MODEL_TYPE: "peft" (default) oppure "full"
- BASE_MODEL_NAME: base model per adapter PEFT (default: meta-llama/Llama-2-7b-chat-hf)
- HF_TOKEN: token Hugging Face opzionale (necessario per modelli gated)
- MAX_MEMORY_TURNS: numero turni in memoria (default: 4)
- LOAD_IN_4BIT: true/false (default: true)
"""

import os
import re
import warnings
from typing import List, Tuple

import gradio as gr
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

warnings.filterwarnings("ignore", category=UserWarning)

MODEL = None
TOKENIZER = None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_dtype() -> torch.dtype:
    value = os.getenv("TORCH_DTYPE", "float16").strip().lower()
    if value == "bfloat16":
        return torch.bfloat16
    if value == "float32":
        return torch.float32
    return torch.float16


def _get_memory_turns() -> int:
    raw_value = os.getenv("MAX_MEMORY_TURNS", "4").strip()
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 4


def load_reson_model():
    model_repo = os.getenv("MODEL_REPO", "Nexus-Walker/Reson").strip()
    model_type = os.getenv("MODEL_TYPE", "peft").strip().lower()
    base_model_name = os.getenv("BASE_MODEL_NAME", "meta-llama/Llama-2-7b-chat-hf").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip() or None
    torch_dtype = _get_dtype()
    load_in_4bit = _env_bool("LOAD_IN_4BIT", True)

    if model_type not in {"peft", "full"}:
        raise ValueError("MODEL_TYPE deve essere 'peft' o 'full'.")

    print(f"Caricamento modello da Hugging Face: {model_repo} (type={model_type})")

    if load_in_4bit and not torch.cuda.is_available():
        print("CUDA non disponibile: LOAD_IN_4BIT disattivato automaticamente.")
        load_in_4bit = False

    quantization_config = None
    if load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch_dtype,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    tokenizer_repo = base_model_name if model_type == "peft" else model_repo
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_repo,
        token=hf_token,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
        "low_cpu_mem_usage": True,
        "torch_dtype": torch_dtype,
        "token": hf_token,
    }
    if quantization_config is not None:
        model_kwargs["quantization_config"] = quantization_config

    if model_type == "peft":
        base_model = AutoModelForCausalLM.from_pretrained(base_model_name, **model_kwargs)
        model = PeftModel.from_pretrained(base_model, model_repo, token=hf_token)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_repo, **model_kwargs)

    model.eval()
    print("Modello caricato correttamente.")
    return model, tokenizer


def minimal_clean_response(response: str) -> str:
    # Rimuove testo tra parentesi quadre e normalizza gli spazi.
    cleaned = re.sub(r"\[.*?\]", "", response)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _extract_turns_from_history(history) -> List[Tuple[str, str]]:
    turns: List[Tuple[str, str]] = []
    if not history:
        return turns

    # Supporta sia formato tuples (legacy) che messages (role/content).
    if isinstance(history[0], (list, tuple)):
        for item in history:
            if len(item) != 2:
                continue
            question = (item[0] or "").strip()
            answer = (item[1] or "").strip()
            if question and answer:
                turns.append((question, answer))
        return turns

    pending_user = None
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user:
            turns.append((pending_user, content))
            pending_user = None
    return turns


def format_conversation_prompt(history, current_question: str) -> str:
    max_memory_turns = _get_memory_turns()
    turns = _extract_turns_from_history(history)

    prompt_parts = []
    for question, answer in turns[-max_memory_turns:]:
        prompt_parts.append(f"[INST] {question} [/INST] {answer}")

    prompt_parts.append(f"[INST] {current_question} [/INST]")
    return " ".join(prompt_parts)


def generate_response(model, tokenizer, prompt: str) -> str:
    max_input_length = int(os.getenv("MAX_INPUT_TOKENS", "2048"))
    max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "300"))

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=max_input_length,
    )

    model_device = model.get_input_embeddings().weight.device
    if model_device.type == "meta":
        model_device = next(model.parameters()).device
    inputs = {k: v.to(model_device) for k, v in inputs.items()}
    input_length = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=float(os.getenv("TEMPERATURE", "0.60")),
            do_sample=True,
            top_p=float(os.getenv("TOP_P", "0.94")),
            top_k=int(os.getenv("TOP_K", "40")),
            repetition_penalty=float(os.getenv("REPETITION_PENALTY", "1.15")),
            no_repeat_ngram_size=int(os.getenv("NO_REPEAT_NGRAM_SIZE", "3")),
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True,
        )

    new_tokens = outputs[0][input_length:]
    raw_response = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    ).strip()
    return minimal_clean_response(raw_response)


def get_model_and_tokenizer():
    global MODEL, TOKENIZER
    if MODEL is None or TOKENIZER is None:
        MODEL, TOKENIZER = load_reson_model()
    return MODEL, TOKENIZER


def chat_fn(message, history):
    if not message or not message.strip():
        return "Scrivi una domanda."

    try:
        model, tokenizer = get_model_and_tokenizer()
        prompt = format_conversation_prompt(history, message.strip())
        response = generate_response(model, tokenizer, prompt)
        return response
    except Exception as exc:
        return f"Errore durante la generazione: {exc}"


def build_app() -> gr.ChatInterface:
    return gr.ChatInterface(
        fn=chat_fn,
        type="messages",
        title="RESON Chat",
        description=(
            "Chat con modello fine-tuned su Hugging Face. "
            "Default: Nexus-Walker/Reson (PEFT su Llama-2-7b-chat-hf)."
        ),
        examples=[
            "Spiegami in modo semplice cos'e il fine-tuning.",
            "Fammi un riassunto dei punti chiave emersi finora.",
        ],
    )


def main():
    app = build_app()
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    share = _env_bool("GRADIO_SHARE", False)
    app.launch(server_name=server_name, server_port=server_port, share=share)


if __name__ == "__main__":
    main()
