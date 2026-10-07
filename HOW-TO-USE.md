# Strata on this PC — how to start it and how to test it

Everything lives in `D:\llm-dev\strata`; the model files are in `C:\Users\maddo\.lmstudio\models`
(the raw GGUF, the pack, the MTP draft layer). Engine 0.1.38, model Qwen3.8-Flash-Next IQ2_XS, 128K context,
`int8` KV, `en` draft subset, one RX 7900 XTX.

## Start

Double-click **`D:\llm-dev\strata\run-iq2_xs.bat`** (or `START-HERE.bat` if you ever re-run setup).

* A window opens and stays open; your browser opens **http://127.0.0.1:8080** when the model is ready.
* First start after a boot takes ~1-2 minutes: the PC can be slow or stop responding for a minute while it loads
  ~20 GiB of experts into RAM and fills ~15 GiB of VRAM. That is normal; don't close the window.
* **Close that window to stop the model.** Nothing else to stop.
* Start it in its own window rather than from an AI/terminal session you later close — if the parent process dies,
  the server dies with it (this is what looked like a crash once: it was the launching process being cleaned up,
  not Strata failing).

## Test it

**Browser** — http://127.0.0.1:8080 : *Chat* (streaming answers, folded thinking, code copy button, sampling and
thinking-level controls), *Monitor* (tokens/s, prompt progress, GPU load, expert-cache hit rate), *About*.

**Terminal** — from `D:\llm-dev\strata`:

```bat
.venv\Scripts\python chat.py --think low
```

Slash commands: `/think none|low|medium|high`, `/reset`, `/image <path>` (only if images were set up), `/quit`.

**API (OpenAI shape)** — any API key, any model name:

```bat
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/v1/models
curl http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"strata\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in five words.\"}],\"max_tokens\":64,\"reasoning_effort\":\"none\"}"
```

`reasoning_effort`: `none` (fastest) / `low` / `medium` / `high` (best for hard questions, and much slower).

**API (Anthropic shape)** — `http://127.0.0.1:8080/v1/messages` (this is what Claude Code wants):

```bat
set ANTHROPIC_BASE_URL=http://127.0.0.1:8080
set ANTHROPIC_AUTH_TOKEN=any
set ANTHROPIC_MODEL=claude-sonnet-4
```

**Point any coding agent / app at it:** provider = OpenAI-compatible, base URL
`http://127.0.0.1:8080/v1`, API key = anything, model name = anything.

**Measure it** (the local bench written during setup; the server must be running):

```bat
.venv\Scripts\python local-bench.py "my pass 1"
```

It posts five fixed prompts and appends the server's own timings to `bench-raw.csv`;
`bench-results-tidy.csv` is the collected set of all passes so far.

## What to expect, honestly

| | measured on this PC |
| --- | --- |
| Decode (answers) | ~60-105 tok/s warm, ~30-60 tok/s in a "cold" pass |
| Prefill (reading your prompt) | ~450-690 tok/s; ~420 on a 1,100-token prompt, ~733 on a 4,500-token one, ~748 on a 125k one |
| Read a 4,478-token prompt | ~6-7 s |
| Cold answer after start | 0.3-1.5 s |

* **The box swings between two states (~2-3x)**: the first request after a fresh start is the fastest, later ones
  can halve. Likely the 20.4 GiB resident expert tier competing with the OS cache for the 28.8 GB PLE table on
  32 GB of RAM. `--low-ram mmap` is the untested A/B that would settle it.
* **One request at a time** — a second request waits.
* **Every answer re-reads the conversation**, so very long chats get slow to start answering (roughly a minute per
  30k tokens of history at this box's prefill speed). `/reset` in chat.py or a new chat in the browser menu.
* **No images** on AMD/Windows (the CPU image encoder is Linux-only), and one GPU only.
* **Reaching it from your phone/another PC** needs a key: `run-iq2_xs.bat` won't do it — run
  `START-HERE.bat --host 0.0.0.0 --api-key <something>` once and use that key in the app. Never expose it without one.

## Change settings

```bat
cd /d D:\llm-dev\strata
.venv\Scripts\python setup.py --setup --yes --family qwen --model IQ2_XS --context 65536 --no-start
.venv\Scripts\python setup.py --setup --yes --family qwen --model IQ2_XS --kv q4_0 --no-start
.venv\Scripts\python setup.py --update --yes
```

Useful flags: `--context N`, `--kv int8|k8v4|q4_0`, `--low-ram auto|resident|mmap`, `--draft-vocab cjk|en|cyrillic`,
`--vram-reserve-mib N`, `--port N`, `--no-start`. `setup.py --help` lists all of them; `START-HERE.bat --check`
re-checks the PC.

## When something looks wrong

| Symptom | Where to look |
| --- | --- |
| No answer / browser can't connect | is the window still open? `curl http://127.0.0.1:8080/health` |
| Slow, disk light busy | not enough free RAM: close other apps, then restart the model |
| `port 8080 is already in use` | an older Strata window is still open (or another app holds 8080) |
| Anything else | `strata-iq2_xs.log` in `D:\llm-dev\strata`, and the window's output |
| To report upstream | attach `strata-iq2_xs.log` + `setup-run.log` to https://github.com/Niko1221/Strata/issues |

Full background, measurements and all deviations from the upstream-supported config: `SETUP-REPORT.md` in the same
folder.
