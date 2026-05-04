# Training data (JSONL)

This folder contains small instruction-style datasets for fine-tuning small LLMs (SLMs)
to act as DSL copilots.

## Structure

- `training/atlas/train.jsonl` — Atlas `.atl`
- `training/neptune/train.jsonl` — Neptune `.nep`
- `training/hydra/train.jsonl` — Hydra `.hyd`
- `training/chronos/train.jsonl` — Chronos `.chr`
- `training/athena/train.jsonl` — Athena `.ath`

Each line is a single JSON object:

```json
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."},
{"role": "assistant", "content": "..."}]}
```

Notes:
- The assistant responses are **code-only** (no prose) for code-generation fine-tuning.
- Paths in examples are written relative to the sample scripts (matching the repo examples).

## Colab

See `training/colab/train_5_adapters_from_drive.py` for a ready-to-run Colab script that:
- mounts Google Drive
- reads the 5 JSONL datasets from Drive
- trains 5 LoRA adapters (1 base SLM + 5 adapters)
- saves adapters back to Drive

See `training/colab/chat_ui_gradio_from_drive.py` for a black-themed Gradio UI that:
- loads 1 base SLM + 1 adapter from Drive
- serves a shareable public URL (Colab `share=True`)

See `training/colab/train_5_adapters_transformers_trainer.py` for a TRL-free trainer script
that avoids `SFTTrainer` API/version issues.
