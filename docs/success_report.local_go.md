# Local LLM Benchmark — Golang Brief & Harness Experiment

Fork-only experiment (host `192.168.15.201`, Apple Mac Studio, 36 GB unified memory, Ollama MLX models). Not part of the upstream maintainer's runs — the maintainer has no local Ollama on macOS. This report consolidates a Go-stack port of the benchmark and shows that **local agentic coding can produce a working, end-to-end-validated app — given the right recipe.**

## Headline result

**A local model built a Go chat app that compiles, tests, builds in Docker, runs, and answers a real chat request — entirely offline.** The winning configuration:

> **`qwen3.5:36b-a3b-coding-nvfp4`** (coding-tuned MoE, ~3B active) · **Zed native agent** · **micro-LLM fallback** (`qwen2.5:0.5b`) · **context summarized between phases**

This is the only run, across every model and harness tried, that completed phase 2 (runtime validation) end-to-end. It is also the first to satisfy the experiment's load-bearing requirement: **the generated app's chat actually responded via the Ollama fallback with no cloud key.**

The path to it took ~10 runs and surfaced four findings the upstream cloud-focused reports do not cover (harness dominance, an Ollama-version regression, a quantization-degeneration effect, and the context×memory ceiling). Those are documented below as the steps that led to the recipe.

## What was tested

A second brief was added to the harness via a new `--brief <manifest>` flag. It mirrors the Rails brief but targets Go and adds one twist aimed at *actually exercising the chat locally*:

1. Go web app, newest Go from **mise**
2. ChatGPT-like SPA: `net/http` + **templ** + **htmx** + **Tailwind**
3. Componentized; run `templ generate`
4. LLM via a **single OpenAI-compatible client behind an interface**
5. **Ollama fallback**: if `OPENROUTER_API_KEY` is empty, use `OLLAMA_BASE_URL` (default `192.168.15.201`) + `OLLAMA_MODEL` — so the chat works locally with no cloud key
6. Table-driven tests with the LLM mocked
7. `gofmt` / `go vet` / `golangci-lint` / `gosec`
8. README, multi-stage Dockerfile, docker-compose

## The winning run — `qwen3.5:36b-a3b-coding` (Zed, two phases)

22-file Go app. **Verified here: `go build ./...` passes, `go test ./...` → `ok llm-chat/tests`, `coverage.out` present.** Phase 2 (run manually, with the context summarized first) built and ran the Docker image and exercised the chat, which **responded via the Ollama fallback**.

What it got right:
- **The fallback — the whole point — is correct and proven working.** `services/openrouter.go`: `defaultOllamaURL = "http://192.168.15.201:11434/v1"` (correct IP), `defaultOllamaModel = "qwen2.5:0.5b"` (the micro model), `client_factory.go` selects OpenRouter when the key is set else Ollama. The chat returned a real completion offline.
- Clean service layer: `services/{chat_service, client_factory, llm, ollama, openrouter}.go`, `handlers/chat_handler.go`, `main.go`, tests in `tests/`.
- Docker is **buildable** this time: multi-stage, **correct `github.com/a-h/templ`** install, and `npm install -g tailwindcss-cli || true` is defensive (won't fail the build). README, docker-compose, `.env.example`, `.gitignore` (the compiled `llm-chat` binary is correctly ignored), `tailwind.config.js`, `mise.toml`.

Two spec deviations — both harmless, both still working:
1. **Used `html/template` (stdlib) instead of templ.** The app renders via `templates/{index.html, templates.go}`; there are zero `.templ` files. Yet the Dockerfile still runs `templ generate` — a **vestigial no-op** (nothing to generate). A simpler, valid rendering choice, but a deviation from the brief, with leftover tooling.
2. **Tailwind via the Play CDN** (`cdn.tailwindcss.com` + inline `tailwind.config`), not a real build. The `tailwind.config.js` and the Docker npm step are then partly vestigial too.

Net: a **strong Tier 2 / near-A** local result — it actually works end to end; the deviations are corner-cuts, not bugs.

### Why this model won

Coding-tuned **MoE (3B active)** is the profile the task needed: fast and low-memory (so it doesn't swap), while still sustaining the agentic loop long enough to assemble app + Docker + chat validation. The earlier candidates each failed one axis — `qwen3.5:27b-mlx` sustained the loop but slower/heavier; the Gemma family didn't sustain it; `qwen3.6:35b` was reasoning-heavy and stalled. The coding-MoE is the local sweet spot.

## Supporting findings (the path to the recipe)

**1. The harness decides Tier for local models — more than the model does.** The same model and prompt (`qwen3.5:27b-mlx`) produced a non-runnable scaffold under opencode but, under Zed's native agent, a complete 21-file phase-1 app (`cmd/web/main.go`, factory fallback with the correct IP, templ + generated `_templ.go`, 4 passing tests, README/Dockerfile/compose). That phase-1 build was Tier 2 with three `docker build`-breaking defects (a **hallucinated `github.com/alecthomas/templ`** import — real is `a-h/templ`; `npm` missing in the golang image; Tailwind wired both CDN and broken-npm). The coding-MoE winner fixed all three. This extends the maintainer's `success_report.multi_model` harness finding (cloud-only) to local, where the gap is Tier 3 vs Tier 2.

**2. Ollama 0.24.0 → 0.30.8 regressed the entire Qwen line.** 0.30.8 returns Qwen output in a separate `reasoning` field with **empty `content`**; opencode does not consume it and **stalls with zero events**. Fix: `reasoning: true` on the model entry restores tool calls (0 → 3 files) but completeness stays below 0.24.0. (Zed handles the field natively — another reason the harness dominates.)

**3. Aggressive quantization causes tool-use degeneration.** `gemma4:26b-mlx` (nvfp4) spiraled into a versioned-file loop (`types_v2.go … types_v18.go`, backtick-corrupted filenames). The same family in **BF16** (`gemma4:12b-mlx-bf16`) wrote clean files — a quant artifact, not the model (though Gemma still didn't sustain the loop).

**4. The real ceiling is context × memory, not capability.** KV cache grows with conversation length; on the 36 GB Mac, swap began ~20k tokens and peaked at **30 GB swap** in a single monolithic session. **Summarizing the context between phase 1 and phase 2** (done for the winning run) kept the KV cache small so phase 2 didn't start from the swap ceiling — the practical version of "decompose into small tasks."

**5. The agent model and the app's runtime model compete for RAM.** When phase 2 first tested the chat, the app's fallback default (`gemma4:26b`, ~18 GB) loaded *on top of* the agent's model (~20 GB) → 40 GB → heavy swap. Fix: the chat fallback must use a **micro LLM** (`qwen2.5:0.5b`, ~0.4 GB) — it only needs to return a non-empty completion to prove the chat works. The prompt default was changed accordingly.

**6. The serving backend, not the model, decides whether Gemma 4 survives — and the `--reasoning-format` fix is `deepseek`, not `none`.** Same **Gemma 4 26B A4B** model, three serving stacks, Go brief + headroom + no subtask, over llama-swap on the Mac Studio:

| backend | serving | channel leak | outcome |
|---|---|---|---|
| `mlm-gemma-4-26B-A4B-it-OptiQ-4bit` | `mlx_lm.server` | leaks → degenerates | **failed** — stall at 11 files |
| `olm-gemma4-26b-mlx` | `ollama serve` | phase1: 0 · **phase2: 2×** | completed (leaked but survived) |
| `clm-gemma-4-26B-A4B-it` | `llama-server` + `--jinja --reasoning-format deepseek` | **0** | **completed, Tier 1** ✅ |

Gemma 4 emits reasoning as harmony/channel tokens (`<channel|>`). If they land in `message.content` instead of a separate reasoning field, the tool-call loop degenerates (`finish_reason=length`, no tool_calls) — the exact stall the raw MLX-lm path hits at file 11. The fix is **`--reasoning-format deepseek`** on `llama-server` (moves thoughts to `reasoning_content`); verified empirically that **`none` LEAVES them in content** (leaks) — the opposite of the older docs (`llama-server` build 9870, [lprsoft-lab/llm-local#5](https://github.com/lprsoft-lab/llm-local/issues/5)). Only the llama.cpp (`clm-`) path exposes that flag. `mlx_lm.server` has no such lever → structurally unfixable. Ollama's native thinking parser catches most channel tokens (single-turn probe clean; phase 1's 80 tool-events clean) but **is not leak-proof**: in phase 2's *continued* session (full phase-1 history + followup), a final summarization turn leaked `thought\n<channel|>` twice into `content`. It survived only by timing (terminal turn, no file corrupted) — mid-session it could degenerate like MLX. **The only robust path for Gemma 4 agentic runs is llama.cpp GGUF + `--reasoning-format deepseek`;** the Ollama-Modelfile-TEMPLATE fix for `gemma4:26b-mlx` is tracked in [lprsoft-lab/llm-local#6](https://github.com/lprsoft-lab/llm-local/issues/6).

## opencode local runs (superseded steps)

| Model | Status | Files | Fallback IP | Note |
|---|---|---:|---|---|
| qwen3.6:27b-mlx | completed_with_errors | 9 | ✅ | Cleanest opencode result: factory + mock + a fallback unit test. No `main`, no frontend. |
| gemma4:12b-mlx-bf16 | completed_with_errors | 3 | ✅ | No degeneration (vs nvfp4); still stops early. |
| qwen3.5:27b-mlx (0.24.0) | completed_with_errors | ~40 | ❌ `192.168.0.90` | Coherent backend, hallucinated the maintainer's IP. |
| qwen3.5:27b-mlx (0.30.8 + reasoning) | completed_with_errors | 3 | — | Stall fixed by `reasoning: true`; thin. |
| qwen3.6:35b-mlx | failed (stall) | ~4 | — | Reasoning-heavy; crawls and stalls. |
| gemma4:26b-mlx | killed | 27 (garbage) | — | nvfp4 degenerate loop. |

For reference, the Rails brief locally: `qwen3.5:27b-mlx` 77 files Tier 2 (correct `RubyLLM.chat`, `.text` accessor bug, 0 tests); the Gemma family Tier 3 (hallucinated `RubyLLM::Client`, or no `ruby_llm` gem, or bare scaffold).

## Harness changes

- **`--brief <manifest.json>`** (`scripts/run_benchmark.py`): bundles prompt + followup + results-dir + report + `project_profile`; explicit CLI flag > manifest > Rails default; no `--brief` = unchanged Rails behavior.
- **`summarize_project` parameterized** (`scripts/benchmark/config.py`): Rails-hardcoded checks moved into a `project_profile`; the Go profile uses `core_globs: ["main.go"]` (matches idiomatic `cmd/<svc>/main.go`) and tests-by-glob (`*_test.go`).
- **Containment via `--dir`** (`scripts/benchmark/runner.py`): opencode anchors to the nearest `.git`; `--dir <project_dir>` keeps the generated app out of the harness repo. (A `git init` boundary was tried first and did not hold.)
- New files: `config/brief.go.json`, `prompts/benchmark_prompt.go.txt`, `prompts/benchmark_followup_prompt.go.txt`, `.gitignore` entries for `results-go/`.

## Operational levers (local + Ollama 0.30.8)

| Lever | When | Effect |
|---|---|---|
| coding-tuned MoE model | always, for local | fast + low-memory + sustains the loop — the single biggest factor |
| Zed (native agent) over opencode | local | handles the 0.30.8 `reasoning` field; Tier 2 vs Tier 3 |
| micro-LLM chat fallback (`qwen2.5:0.5b`) | phase 2 / runtime | app's chat doesn't load a 2nd big model atop the agent's |
| summarize context between phases | phase 2 | KV cache stays small; no swap from a 30 GB-context start |
| `reasoning: true` | opencode + Ollama 0.30.8 + Qwen | fixes the zero-event stall |
| `limit.context: 16384`, `limit.output: 16384` | ≤36 GB hardware | cap KV growth below swap; avoid mid-reasoning truncation |
| BF16 over nvfp4/Q4 | Gemma | removes the `types_v2…v18` degeneration |
| llama.cpp GGUF + `--jinja --reasoning-format deepseek` | Gemma 4 (agentic) | strips `<channel|>` from content → the only leak-free, Tier 1 path (MLX-lm has no flag; Ollama leaks in continued sessions) |

## Conclusions

- **Local agentic coding works — with the right recipe.** A coding-tuned MoE in a harness that handles the model's output format, with a micro-LLM runtime fallback and context summarized between phases, produced a Go chat app that compiles, tests, dockerizes, runs, and answers offline. That is the deliverable the whole experiment was chasing.
- **Pick the harness as carefully as the model.** Zed extracted a working app from the same model opencode could only scaffold.
- **Newer infra is not automatically better.** Ollama 0.30.8 regressed every Qwen model in opencode via a reasoning/content split; 0.24.0 was better there.
- **Quantization *and the serving backend* are correctness variables** — nvfp4 made Gemma degenerate (BF16 fixed it); and for the *same* Gemma 4 26B, MLX-lm failed / Ollama leaked-but-survived / llama.cpp+`--reasoning-format deepseek` was the only clean Tier 1 (finding #6). Reasoning-format handling lives in the server, and only llama.cpp exposes the lever.
- **The monolithic one-shot brief measures the hardware's context-memory ceiling as much as coding ability.** Context summarization between phases (and, for full automation, decomposition into ~16k sub-tasks with fresh sessions) is the local-specific strategy the upstream cloud reports never needed.

## Reproducing the automatable path

Zed's *native* agent is GUI-only and not scriptable for batch runs (GPUI-rendered, so accessibility-based drivers like Appium/Mac2 struggle). The reproducible route to "better-harness" local benchmarking is **Agent Client Protocol (ACP)** — JSON-RPC over stdio, agent-as-subprocess, editor-as-thin-client — i.e. run ACP agents headlessly. That captures external ACP agents (Claude Code / Gemini CLI / Codex), though not Zed's specific native-agent behavior.
