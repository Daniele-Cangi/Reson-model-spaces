#!/usr/bin/env python3
"""
Entrypoint per Hugging Face Spaces (Gradio).
"""

import os

from chat import build_app

app = build_app()

if __name__ == "__main__":
    app.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        share=False,
    )
