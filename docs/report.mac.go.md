# Benchmark Report

Generated at: 2026-07-10T19:34:47+00:00
Prompt SHA256: `ce0bff42ccf9d4fbde43a283c978d96f20a2079ee6040e2b44fad163fa6d767b`

## Progress

- `completed`: 2
- `completed_with_errors`: 2
- `failed`: 1
- `timeout`: 0
- `not_run`: 9

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
- `qwen3_6_27b_mlx` -> `ollama/qwen/qwen3.6-27b-mlx`: Qwen 3.6 27B Dense model via llama-swap with Ollama/MLX backend on Apple Silicon. Smaller than the 35B A3B MOE variant — uses dense architecture which may produce more reliable tool calling and fewer repetition loops. Fits comfortably in 36 GB unified memory even at higher precision. Tests whether a smaller dense model outperforms larger MOE models on the benchmark. [Mac Studio M4 Max 36GB profile]
- `ornith_9b_bf16` -> `ollama/ornith:9b-bf16`: Ornith 1.0 9B BF16 via llama-swap with Ollama backend on Apple Silicon. Specialized agentic coding model that achieves 69.4% on SWE-Bench Verified despite 9B params. BF16 quantization (~17GB) fits in 36GB unified memory. Tests whether a small specialized model beats larger general models (Qwen 3.5/3.6, Gemma 4) on the benchmark. [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_qwen_qwen` -> `ollama/qwen/qwen3.6-35b-a3b-gguf`: Local-only forced delegation: Qwen 3.6 35B GGUF (planner) + Qwen 3.5 35B Coding MLX (coder), both via llama-swap on Mac Studio. Tests whether a local model pair can execute the planner-orchestrator pattern end-to-end without cloud dependencies. [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_gemma_qwen` -> `ollama/google/gemma4-26b-a4b-it-mlx`: Local-only forced delegation: Gemma 4 26B MLX (planner) + Qwen 3.5 35B Coding MLX (coder), both via llama-swap on Mac Studio. Cross-architecture test: Gemma 4 plans, Qwen coding variant executes. [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_gemma_gemma` -> `ollama/google/gemma4-26b-a4b-it-mlx`: Local-only forced delegation smoke test: Gemma 4 26B MLX as both planner and coder, same model via llama-swap on Mac Studio. Tests whether the same-model setup can sustain the planner-orchestrator loop (tool calling reliability, context handling) without cloud dependencies. [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_qwen_qwen_same` -> `ollama/qwen/qwen3.6-35b-a3b-gguf`: Local-only forced delegation: Qwen 3.6 35B GGUF as both planner and coder, same model via llama-swap on Mac Studio. No model switching cost. Tests whether Qwen 3.6 sustains the planner-orchestrator loop better than Gemma 4 26B (which stalled). [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_qwen35_qwen35_same` -> `ollama/qwen/qwen3.5-35b-a3b-coding-mlx`: Local-only forced delegation: Qwen 3.5 35B Coding MLX as both planner and coder, same model via llama-swap on Mac Studio. Tests whether the coding-optimized variant sustains the planner-orchestrator loop better than Qwen 3.6 GGUF or Gemma 4 26B MLX (both stalled). [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_qwen27_qwen27_same` -> `ollama/qwen/qwen3.6-27b-mlx`: Local-only forced delegation: Qwen 3.6 27B Dense MLX as both planner and coder, same dense model via llama-swap on Mac Studio. First test of a dense (non-MOE) architecture in the planner-orchestrator loop. 27B active params vs ~3-4B on MOE variants — hypothesize better tool calling reliability and fewer repetition loops. 64k context due to dense model overhead in 36GB unified memory. [Mac Studio M4 Max 36GB profile]
- `mac_local_forced_qwen_ornith` -> `ollama/qwen/qwen3.6-35b-a3b-gguf`: Local-only forced delegation: Qwen 3.6 35B GGUF (planner) + Ornith 9B BF16 (coder), both via llama-swap on Mac Studio. Tests whether the SWE-Bench specialized small model (Ornith) executes better than a larger general model when guided by a planner. [Mac Studio M4 Max 36GB profile]

## Results

| Model | Provider | Warmup ctx | Status | Elapsed (s) | Total tokens | Tok/s | Works? | Files | Notes |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- |
| Gemma 4 26B MLX | ollama | - | failed | 591.37 | 24002 | 40.59 | partial | 11 | Exit code -15. Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Gemma 4 26B Ollama MLX | ollama | - | completed | 1273.73 | 75294 | 209.42 | yes | 17 | Go module, tests, README, and container files detected. |
| Gemma 4 26B GGUF | ollama | - | completed | 2129.25 | 14885 | 17.44 | yes | 26 | Exit code -15. Go module, tests, README, and container files detected. |
| Qwen 3.6 35B A3B GGUF | ollama | - | completed_with_errors | 1462.87 | 6474 | 10.84 | partial | 603 | Exit code -15. Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Qwen 3.5 35B A3B Coding MLX | ollama | - | completed_with_errors | 1049.50 | 49223 | 55.20 | partial | 9 | Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Qwen 3.6 27B Dense MLX | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Ornith 1.0 9B BF16 | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Qwen 3.6 -> Qwen 3.5 Coding (FORCED delegation) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Gemma 4 26B -> Qwen 3.5 Coding (FORCED delegation) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Gemma 4 26B -> Gemma 4 26B (FORCED delegation, same-model smoke) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Qwen 3.6 -> Qwen 3.6 (FORCED delegation, same-model) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Qwen 3.5 Coding -> Qwen 3.5 Coding (FORCED delegation, same-model) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Qwen 3.6 27B -> Qwen 3.6 27B (FORCED delegation, same-model, dense) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Mac local Qwen 3.6 -> Ornith 9B (FORCED delegation) | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |

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

