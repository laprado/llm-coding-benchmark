# Local Provider Status — Mac Studio (MLX profile)

Last checked: 2026-07-11.

This is the Mac Studio counterpart to [`docs/local-provider-status.md`](local-provider-status.md)
(which documents the maintainer's AMD homeserver at `192.168.0.90`). This profile is
**not** part of upstream — it tracks my own local inference box and lives on the
`feat_ollama_mlx` experimentation branch.

Source of truth: [`~/lprsoft/llm-local`](https://github.com/laprado/llm-local) — the
Mac Studio runs **mlx-lm**, **llama.cpp** and **ollama** behind a single
**llama-swap** endpoint that hot-swaps the loaded model on demand. This status is
compiled from `llama-swap/config.yaml` (config inspection), not a full live probe;
tool-calling behavior below is verified with `scripts/test-tool-calling.sh`.

## Homeserver: Mac Studio (M4 Max, 36 GB unified)

### llama-swap (`http://192.168.15.201:8080/v1`)

Single OpenAI-compatible endpoint. Model swap is driven by the `model` field of the
request; the client always hits the same URL. The `local` group is **exclusive**
(`swap: true`, `exclusive: true`) — **only one model is resident at a time**, because
36 GB of unified memory saturates fast. Served as a headless LaunchDaemon
(`scripts/llama-swap.plist`, `--listen 0.0.0.0:8080`).

### Naming convention (backend prefix)

The external model id carries a backend prefix so the *same* model can run on
different backends and be compared side by side (tool-calling behavior varies):

| Prefix | Backend | Tool | `--reasoning-format` support |
|---|---|---|---|
| `mlm-` | MLX | `mlx_lm.server` | ✗ (no flag — see finding below) |
| `clm-` | llama.cpp | `llama-server` | ✓ (`deepseek`, via `llama_common` macro) |
| `olm-` | ollama | `ollama serve` | n/a (server-side chat template) |

### Configured models (`local` group)

| External id | Backend | Internal model | ctx | ttl |
|---|---|---|---|---|
| `mlm-Qwen2.5-0.5B-Instruct-4bit` | MLX | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` | default | 300 |
| `mlm-gemma-4-26B-A4B-it-OptiQ-4bit` | MLX | `mlx-community/gemma-4-26B-A4B-it-OptiQ-4bit` | default | 600 |
| `olm-gemma4-26b-mlx` | ollama | `gemma4:26b-mlx` | default | 600 |
| `olm-qwen3.5-35b-a3b-coding-nvfp4` | ollama | `qwen3.5:35b-a3b-coding-nvfp4` | default | 600 |
| `olm-ornith-9b-bf16` | ollama | `ornith:9b-bf16` | default | 600 |
| `olm-qwen3.6-27b-mlx` | ollama | `qwen3.6:27b-mlx` | default | 600 |
| `clm-qwen3.6-35b-a3b` | llama.cpp | `unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_M` (`-hf`) | 32768 | 600 |
| `clm-gemma-4-26B-A4B-it` | llama.cpp | `unsloth/gemma-4-26B-A4B-it-GGUF:Q4_K_M` (`-hf`) | 32768 | 600 |

Three backends serve the **same** Gemma 4 26B A4B (`mlm-`, `olm-`, `clm-`), which is
the whole point: it lets me compare MLX × Ollama × llama.cpp on identical weights.

## Finding: `--reasoning-format` is a `clm-`-only fix (MLX leaks channel tokens)

Channel/harmony models (Gemma 4, Qwen 3.5/3.6) emit reasoning as separate channels
(`<|channel|>`, `<think>`). If those tokens leak into `message.content`, the client's
tool-calling loop stalls (channel-leak → stall). The fix is server-side:

- **`clm-` (llama.cpp)** — inherit `--reasoning-format deepseek` globally via the
  shared `llama_common` macro in `config.yaml`, which moves thoughts to
  `message.reasoning_content` and keeps `content` clean → `finish_reason=tool_calls`.
  ✅ This is applied to every `clm-` model.
- **`mlm-` (MLX)** — `mlx_lm.server` has **no `--reasoning-format` flag at all**, so
  the leak is **not** fixable by a launch flag here. A fix would require overriding the
  chat template. For reliable tool-calling with Gemma 4, prefer the GGUF path
  (`clm-gemma-4-26B-A4B-it`) over `mlm-gemma-4-26B-A4B-it-OptiQ-4bit`.
- **`olm-` (ollama)** — reasoning handling is the ollama chat template's job; not a
  `--reasoning-format` matter.

Note: `--reasoning-format none` does **not** fix the leak (by design it leaves thoughts
unparsed in `content`); `deepseek` is the correct value. Verified against
`llama-server --help` (build 9870) and a live tool-call probe — see
[lprsoft-lab/llm-local#5](https://github.com/lprsoft-lab/llm-local/issues/5) and the
`--reasoning-format` section of [`docs/llama-swap.md`](llama-swap.md).

This is why the benchmark's `gemma4_26b_mlx` run stalled while the GGUF path completes.

## Harness relationship

The benchmark harness (`scripts/benchmark/backends.py`, `LlamaSwapBackend`) is a plain
HTTP client of `/v1/chat/completions` — it configures context per-request only where the
backend allows and otherwise treats reasoning-format/serving as server-side. It cannot
set `--reasoning-format`; that lives in the llama-swap config on this box. Point the
benchmark at this endpoint with:

```bash
python scripts/run_benchmark.py --local-backend llama-swap \
  --local-api-base http://192.168.15.201:8080
```

## Validation

Tool-calling parity across backends is checked from the client with
`scripts/test-tool-calling.sh` in `llm-local` (same prompt + same tool per model,
classifies `✅ tool_call` / `⚠️ texto` / `❌ erro`):

```bash
MAC=192.168.15.201 PORT=8080 bash scripts/test-tool-calling.sh \
  mlm-gemma-4-26B-A4B-it-OptiQ-4bit clm-gemma-4-26B-A4B-it
```

Expected: `clm-` returns a structured `tool_call`; `mlm-` degenerates to text / channel
leak on Gemma 4.
