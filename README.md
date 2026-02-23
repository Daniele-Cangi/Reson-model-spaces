---
title: Reson Chat
emoji: 🧠
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
python_version: "3.10"
app_file: app.py
pinned: false
---

# RESON Gradio Chat

Package pronto per:
- avvio locale
- deploy diretto su Hugging Face Spaces

Default configurato:
- `MODEL_REPO=Nexus-Walker/Reson`
- `MODEL_TYPE=peft`
- `BASE_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf`

## Avvio locale (PowerShell)

1. Copia `.env.example` in `.env` e inserisci il token.
2. Avvia:

```powershell
.\run_local.ps1
```

Oppure manuale:

```powershell
pip install -r requirements.txt
$env:HF_TOKEN = "hf_xxx"
python app.py
```

Apri: `http://localhost:7860`

## Deploy su Hugging Face Spaces

1. Crea uno Space Gradio (consigliato GPU se usi Llama-2-7b).
2. Carica questi file nello Space (`app.py`, `chat.py`, `requirements.txt`, `README.md`).
3. In `Settings -> Variables and secrets` aggiungi:
- `HF_TOKEN` come Secret
- (alternativa) `HUGGINGFACEHUB_API_TOKEN` oppure `HF_API_TOKEN`
- opzionali: `MODEL_REPO`, `MODEL_TYPE`, `BASE_MODEL_NAME`
4. Riavvia lo Space.

Nota runtime:
- questo Space e configurato per `python_version: 3.10` (compatibilita con dipendenze Gradio/Audio)
- evitare Python 3.13 su questo progetto

## Flusso GitHub -> Spaces (si, e possibile)

Puoi usare una repo GitHub come sorgente e pushare lo stesso branch anche su Hugging Face Space.

1. Crea:
- repo GitHub (es: `Nexus-Walker/reson-gradio`)
- Space HF (es: `Nexus-Walker/Reson-model`)
2. Esegui:

```powershell
.\publish_remotes.ps1 -GitHubRepo "Daniele-Cangi/Reson-model-spaces" -HfSpaceRepo "Nexus-Walker/Reson-model"
```

Questo script:
- imposta remote `github`
- imposta remote `hfspace`
- fa push del branch `main` su entrambi

### Sync automatico da GitHub a Space

Nel repo e gia incluso `.github/workflows/sync-space.yml`.

Configura in GitHub:
1. `Settings -> Secrets and variables -> Actions -> Secrets`
- `HF_TOKEN` = token Hugging Face (fine-grained, read/write)
2. `Settings -> Secrets and variables -> Actions -> Variables`
- `HF_SPACE_REPO` = `Nexus-Walker/Reson-model`

Dopo questo, ogni push su `main` fa deploy automatico allo Space.

## Key Hugging Face: serve?

Sì, nel tuo caso consigliata/necessaria:
- l'adapter `Nexus-Walker/Reson` puo essere pubblico o privato
- la base `meta-llama/Llama-2-7b-chat-hf` è gated

Quindi devi impostare `HF_TOKEN` e accettare la licenza Llama 2 dal tuo account Hugging Face.

Tipo token consigliato:
- Fine-grained `Read` per runtime inferenza
- `Write` solo se vuoi fare push programmatico su Hugging Face

## Variabili opzionali

- `MAX_MEMORY_TURNS` (default `4`)
- `LOAD_IN_4BIT` (default `true`)
- `MAX_INPUT_TOKENS` (default `2048`)
- `MAX_NEW_TOKENS` (default `300`)
- `TEMPERATURE` (default `0.60`)
- `TOP_P` (default `0.94`)
- `TOP_K` (default `40`)
- `REPETITION_PENALTY` (default `1.15`)
- `NO_REPEAT_NGRAM_SIZE` (default `3`)
