"""Colab script: code-generation UI for Atlas-suite adapters (Gradio).

What it does:
- mounts Google Drive
- installs deps
- loads 1 base SLM + 1 selected LoRA adapter (atlas/neptune/hydra/chronos/athena)
- serves a black-themed product-style code generation UI
- prints a public URL when `share=True`
Usage (in Colab):
!python training/colab/chat_ui_gradio_from_drive.py
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Paths:
    drive_root: str = "/content/drive/MyDrive/atlas"
    adapters_root: str = "/content/drive/MyDrive/atlas/adapters"
    outputs_root: str = "/content/drive/MyDrive/atlas/generated"


BASE_MODEL_DEFAULT = "Qwen/Qwen2.5-0.5B-Instruct"


BLACK_CSS = """
html, body, .gradio-container {
  background: #0b0f14 !important;
  color: #e6edf3 !important;
}
.gradio-container * { color: #e6edf3; }
textarea, input, select {
  background: #0f1520 !important;
  color: #e6edf3 !important;
  border: 1px solid #1f2a3a !important;
}
.gr-input, .gr-box, .gr-panel, .gr-form, .gr-accordion, .gr-group {
  background: #0d1117 !important;
  border-color: #1f2a3a !important;
}
.gradio-container a { color: #58a6ff !important; }
.gradio-container .gr-markdown h1,
.gradio-container .gr-markdown h2,
.gradio-container .gr-markdown h3 { color: #e6edf3 !important; }
.gradio-container .gr-markdown code {
  background: #0f1520 !important;
  border: 1px solid #1f2a3a !important;
  padding: 2px 6px !important;
  border-radius: 6px !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace !important;
}
.prose, .markdown, .message {
  color: #e6edf3 !important;
}
.message.user {
  background: #0f1520 !important;
  border: 1px solid #1f2a3a !important;
}
.message.bot {
  background: #0d1117 !important;
  border: 1px solid #1f2a3a !important;
}
button {
  background: #1f6feb !important;
  border: 1px solid #1f6feb !important;
  color: #ffffff !important;
}
button.secondary {
  background: #0f1520 !important;
  border: 1px solid #1f2a3a !important;
}
"""


def main() -> int:
    # 1) Mount Drive
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive")

    # 2) Install deps (UI + inference stack)
    os.system(
        "pip -q install -U gradio transformers peft accelerate bitsandbytes sentencepiece"
    )

    # 3) Lazy imports (after pip)
    import gradio as gr
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    paths = Paths()

    def list_adapters() -> list[str]:
        if not os.path.isdir(paths.adapters_root):
            return []
        out = []
        for name in sorted(os.listdir(paths.adapters_root)):
            p = os.path.join(paths.adapters_root, name)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, "adapter_config.json")):
                out.append(name)
        return out

    def load_model(base_model: str, adapter_name: str):
        adapter_dir = os.path.join(paths.adapters_root, adapter_name)
        tok = AutoTokenizer.from_pretrained(base_model, use_fast=True, trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            load_in_4bit=True,
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(base, adapter_dir)
        model.eval()
        return tok, model

    def build_prompt(system: str, history: list[tuple[str, str]], user: str) -> str:
        # Keep prompt simple and deterministic. Your datasets used this format.
        parts = [f"<|system|>\n{system}\n"]
        for u, a in history:
            parts.append(f"<|user|>\n{u}\n")
            parts.append(f"<|assistant|>\n{a}\n")
        parts.append(f"<|user|>\n{user}\n")
        parts.append("<|assistant|>\n")
        return "".join(parts)

    def generate(tok, model, prompt: str, max_new_tokens: int, temperature: float, top_p: float):
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=int(max_new_tokens),
                do_sample=temperature > 0,
                temperature=float(temperature),
                top_p=float(top_p),
                eos_token_id=tok.eos_token_id,
                pad_token_id=tok.eos_token_id,
            )
        text = tok.decode(out[0], skip_special_tokens=False)
        # Return only the new assistant chunk
        return text.split("<|assistant|>\n", 1)[-1].strip()

    # Cache currently loaded model
    state = {
        "tok": None,
        "model": None,
        "base": BASE_MODEL_DEFAULT,
        "adapter": None,
        "last_code": "",
    }

    def adapter_ext(name: str) -> str:
        return {
            "atlas": "atl",
            "neptune": "nep",
            "hydra": "hyd",
            "chronos": "chr",
            "athena": "ath",
        }.get(name, "txt")

    def on_load_adapter(base_model: str, adapter_name: str):
        if not adapter_name:
            return "No adapter selected."
        t0 = time.time()
        tok, model = load_model(base_model, adapter_name)
        state["tok"] = tok
        state["model"] = model
        state["base"] = base_model
        state["adapter"] = adapter_name
        dt = time.time() - t0
        return f"Loaded adapter: {adapter_name} (base={base_model}) in {dt:.1f}s"

    def chat(
        system: str,
        message: str,
        history,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
    ):
        if state["tok"] is None or state["model"] is None:
            return history, "Load an adapter first.", state["last_code"]
        prompt = build_prompt(system, history, message)
        reply = generate(state["tok"], state["model"], prompt, max_new_tokens, temperature, top_p)
        # Force code presentation in chat + dedicated code panel
        state["last_code"] = reply.strip()
        history = history + [(message, f"```text\n{state['last_code']}\n```")]
        return history, "", state["last_code"]

    def save_last_code(adapter_name: str, code: str, filename: str) -> str:
        if not code.strip():
            return "Nothing to save."
        if not adapter_name:
            return "Select an adapter first."
        ext = adapter_ext(adapter_name)
        base = filename.strip() or f"{adapter_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if "." in base:
            base = base.rsplit(".", 1)[0]
        os.makedirs(paths.outputs_root, exist_ok=True)
        out_path = os.path.join(paths.outputs_root, f"{base}.{ext}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(code.rstrip() + "\n")
        return f"Saved: {out_path}"

    def preset_text(adapter_name: str, kind: str) -> str:
        a = adapter_name or "atlas"
        # Keep prompts short; model is trained for code-only.
        base = {
            "atlas": "Generate an Atlas .atl script to",
            "neptune": "Generate Neptune code to",
            "hydra": "Generate Hydra code to",
            "chronos": "Generate Chronos code to",
            "athena": "Generate Athena code to",
        }.get(a, "Generate code to")
        if kind == "risk":
            return f"{base} compute VaR/ES from prices.csv and print the result."
        if kind == "etl":
            return f"{base} load prices.csv, clean it, and compute a diff/normalize pipeline."
        if kind == "pricing":
            return f"{base} load options + vol surface and print Greeks and prices."
        if kind == "ml":
            return f"{base} build features and train a model on close, then print predictions."
        return f"{base} do the standard example for this DSL."

    adapters = list_adapters()
    if not adapters:
        print("No adapters found under:", paths.adapters_root)
        print("Train adapters first with: training/colab/train_5_adapters_from_drive.py")

    with gr.Blocks(css=BLACK_CSS, theme=gr.themes.Base()) as demo:
        gr.Markdown("## Atlas Suite Copilot")
        gr.Markdown(
            "Code-generation UI (base SLM + LoRA adapter). "
            "Load an adapter, describe what you want, and copy/save the generated DSL."
        )

        with gr.Row(equal_height=True):
            # --- Left sidebar ---
            with gr.Column(scale=1, min_width=320):
                gr.Markdown("### Settings")
                base_model = gr.Textbox(value=BASE_MODEL_DEFAULT, label="Base model")
                adapter = gr.Dropdown(
                    choices=adapters,
                    value=adapters[0] if adapters else None,
                    label="Adapter",
                )
                load_btn = gr.Button("Load adapter")
                status = gr.Textbox(value="", label="Status", interactive=False)
                load_btn.click(on_load_adapter, inputs=[base_model, adapter], outputs=[status])

                system = gr.Textbox(
                    value="Return only runnable DSL code. No explanations. No markdown fences.",
                    label="System prompt",
                )

                gr.Markdown("### Generation")
                max_new = gr.Slider(64, 1024, value=256, step=16, label="max_new_tokens")
                temp = gr.Slider(0.0, 1.2, value=0.3, step=0.05, label="temperature")
                topp = gr.Slider(0.5, 1.0, value=0.95, step=0.01, label="top_p")

                gr.Markdown("### Quick prompts")
                with gr.Row():
                    btn_risk = gr.Button("Risk", elem_classes=["secondary"])
                    btn_etl = gr.Button("ETL", elem_classes=["secondary"])
                with gr.Row():
                    btn_prc = gr.Button("Pricing", elem_classes=["secondary"])
                    btn_ml = gr.Button("ML", elem_classes=["secondary"])

            # --- Right main panel ---
            with gr.Column(scale=2, min_width=520):
                chatbot = gr.Chatbot(label="Conversation", height=380)

                msg = gr.Textbox(
                    label="What do you want to generate?",
                    placeholder=(
                        "Example: Generate an Atlas .atl script to compute VaR(0.95) "
                        "from prices.csv and print it."
                    ),
                )

                with gr.Row():
                    send = gr.Button("Generate")
                    clear = gr.Button("Clear")

                # Older Gradio versions have a limited language list for Code.
                # Omitting `language` keeps compatibility.
                last_code = gr.Code(label="Last generated code", value="")

                with gr.Row():
                    filename = gr.Textbox(
                        label="Filename (optional)",
                        placeholder="example (no extension needed)",
                    )
                    save_btn = gr.Button("Save to Drive")
                save_status = gr.Textbox(value="", label="Save status", interactive=False)
                save_btn.click(
                    save_last_code,
                    inputs=[adapter, last_code, filename],
                    outputs=[save_status],
                )

        send.click(
            chat,
            inputs=[system, msg, chatbot, max_new, temp, topp],
            outputs=[chatbot, msg, last_code],
        )
        msg.submit(
            chat,
            inputs=[system, msg, chatbot, max_new, temp, topp],
            outputs=[chatbot, msg, last_code],
        )
        clear.click(lambda: ([], ""), outputs=[chatbot, last_code])

        btn_risk.click(lambda a: preset_text(a, "risk"), inputs=[adapter], outputs=[msg])
        btn_etl.click(lambda a: preset_text(a, "etl"), inputs=[adapter], outputs=[msg])
        btn_prc.click(lambda a: preset_text(a, "pricing"), inputs=[adapter], outputs=[msg])
        btn_ml.click(lambda a: preset_text(a, "ml"), inputs=[adapter], outputs=[msg])

    demo.queue()
    demo.launch(share=True, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

