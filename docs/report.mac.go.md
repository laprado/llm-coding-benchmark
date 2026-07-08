# Benchmark Report

Generated at: 2026-07-07T14:41:09+00:00
Prompt SHA256: `cf89c4d279a14df863d0183846a461b2a36679cf55c4c2e0864e9e5d40b66176`

## Progress

- `completed`: 0
- `completed_with_errors`: 4
- `failed`: 2
- `timeout`: 0
- `not_run`: 0

## Runner

`opencode run --agent build --format json`

- Selected after local probing because it exposes machine-readable JSON events with session IDs and token counts.
- The local crush install advertised --yolo in help output but rejected the flag at runtime, which makes it a poor default for unattended benchmarking here.
- The explicit build agent has permissive filesystem/tool rules, which is the closest match to the requested autonomous coding workflow.

## Model Selection

- `gemma4_26b_mlx` -> `ollama/google/gemma4-26b-a4b-it-mlx`: Gemma 4 26B MOE (4B active params) via llama-swap with MLX backend on Apple Silicon. OptiQ 4bit quant fits ~13 GB weights in 36 GB unified memory. Direct comparison with gemma4_31b (llama.cpp) on the AMD profile — tests whether MLX inference on Apple Silicon produces equivalent code quality to llama.cpp on AMD/NVIDIA at similar model scale. [Mac Studio M4 Max 36GB profile]
- `gemma4_26b_ollama` -> `ollama/google/gemma4-26b-a4b-it-ollama`: Gemma 4 26B MOE (4B active params) served by Ollama with MLX backend on Apple Silicon. Head-to-head comparison with gemma4_26b_mlx (same model, mlx-lm backend) to test whether the serving backend affects tool calling reliability, repetition loop behavior, or overall code quality. [Mac Studio M4 Max 36GB profile]
- `gemma4_26b_gguf` -> `ollama/google/gemma4-26b-a4b-it-gguf`: Gemma 4 26B MOE (4B active params) via llama-swap with llama.cpp GGUF backend on Apple Silicon. -hf flag triggers HuggingFace download on first load. Third backend variant for the same model: head-to-head-to-head with gemma4_26b_mlx (MLX-lm) and gemma4_26b_ollama (Ollama/MLX) to compare tool calling reliability and code quality across MLX-lm, Ollama, and llama.cpp serving stacks. [Mac Studio M4 Max 36GB profile]
- `qwen3_6_35b_a3b_gguf` -> `ollama/qwen/qwen3.6-35b-a3b-gguf`: Qwen 3.6 35B MOE (3B active params) via llama-swap with llama.cpp GGUF backend on Apple Silicon. -hf flag triggers HuggingFace download on first load. Direct comparison with qwen3_5_35b_a3b_coding_mlx (MLX NVFP4) and the AMD/NVIDIA qwen3_6_35b profile — tests whether the GGUF/llama.cpp path produces equivalent or better code quality than the MLX path on Apple Silicon. [Mac Studio M4 Max 36GB profile]
- `qwen3_5_35b_a3b_coding_mlx` -> `ollama/qwen/qwen3.5-35b-a3b-coding-mlx`: Qwen 3.5 35B MOE (3B active params) coding variant via llama-swap with MLX backend on Apple Silicon. NVFP4 quantized. Fits comfortably in 36 GB unified memory. Direct comparison with qwen3_5_35b (llama.cpp, AMD) and qwen3_6_35b — tests MLX inference quality vs llama.cpp at same model scale. [Mac Studio M4 Max 36GB profile]
- `ornith_9b_bf16` -> `ollama/ornith:9b-bf16`: Ornith 1.0 9B BF16 via llama-swap with Ollama backend on Apple Silicon. Specialized agentic coding model that achieves 69.4% on SWE-Bench Verified despite 9B params. BF16 quantization (~17GB) fits in 36GB unified memory. Tests whether a small specialized model beats larger general models (Qwen 3.5/3.6, Gemma 4) on the benchmark. [Mac Studio M4 Max 36GB profile]

## Results

| Model | Provider | Warmup ctx | Status | Elapsed (s) | Total tokens | Tok/s | Works? | Files | Notes |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- |
| Gemma 4 26B MLX | ollama | - | failed | 318.77 | 25962 | 81.44 | partial | 20614 | Exit code -15. Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Gemma 4 26B Ollama MLX | ollama | - | completed_with_errors | 566.57 | 33554 | 552.69 | partial | 1116 | Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Gemma 4 26B GGUF | ollama | - | failed | 1653.63 | 32768 | 29.19 | partial | 1307 | Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Qwen 3.6 35B A3B GGUF | ollama | - | completed_with_errors | 1325.88 | 5971 | 10.64 | partial | 1465 | Exit code -15. Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Qwen 3.5 35B A3B Coding MLX | ollama | - | completed_with_errors | 712.53 | 25762 | 138.89 | partial | 1126 | Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Ornith 1.0 9B BF16 | ollama | - | completed_with_errors | 1308.81 | 26747 | 96.24 | no | 5 | Generated files do not resemble the requested Rails project. |

## Per-Run Paths

Each run writes to `results/<slug>/` with these files:

- `project/`: the generated project workspace
- `prompt.txt`: exact prompt used for the run
- `opencode-output.ndjson`: raw JSON event stream from opencode
- `opencode-stderr.log`: stderr from the opencode process
- `followup-prompt.txt`: second-phase validation prompt for continuations when enabled
- `followup-opencode-output.ndjson`: raw JSON event stream from the follow-up continuation
- `followup-opencode-stderr.log`: stderr from the follow-up continuation
- `session-export.json`: exported opencode session snapshot when available
- `result.json`: normalized metadata used for this report

