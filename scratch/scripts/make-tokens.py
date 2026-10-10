#!/usr/bin/env python3
"""Write a token-id file for the engine CLI (which has no tokenizer of its own).

    python make-tokens.py <chars-of-body> <out.txt>

Uses tools/strata_tokenizer.py's Tokenizer against the original GGUF shard that carries the vocabulary, builds
the same ~4K-token prompt shape the A/B used, and writes the ids comma-separated - what `--tokens-file` wants.
"""
import pathlib
import sys

ROOT = pathlib.Path(r"D:\llm-dev\strata")
sys.path.insert(0, str(ROOT / "tools"))
from strata_tokenizer import Tokenizer  # noqa: E402

GGUF = r"C:\Users\maddo\.lmstudio\models\models\IQ2_XS\Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf"
BODY = "The following is a long technical note about GPU memory hierarchies and expert streaming. "

n = int(sys.argv[1]) if len(sys.argv) > 1 else 240
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "logs/prompt-ids.txt")
prompt = BODY * n + "\n\nSummarise the note in one sentence."

tk = Tokenizer.from_gguf(GGUF)
ids = tk.encode(prompt)
out.parent.mkdir(exist_ok=True)
out.write_text(",".join(str(i) for i in ids), encoding="utf-8")
print(f"prompt {len(prompt)} chars -> {len(ids)} tokens -> {out}")
