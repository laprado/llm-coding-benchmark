# Benchmark Report

Generated at: 2026-06-13T14:48:09+00:00
Prompt SHA256: `5c5ed89d91809a4e3e40f9fc0ece3e82d4fd719fc02d95896dfad6e8c879296e`

## Progress

- `completed`: 0
- `completed_with_errors`: 3
- `failed`: 1
- `timeout`: 0
- `not_run`: 57

## Runner

`opencode run --agent build --format json`

- Selected after local probing because it exposes machine-readable JSON events with session IDs and token counts.
- The local crush install advertised --yolo in help output but rejected the flag at runtime, which makes it a poor default for unattended benchmarking here.
- The explicit build agent has permissive filesystem/tool rules, which is the closest match to the requested autonomous coding workflow.

## Model Selection

- `gemma4_31b` -> `ollama/google/gemma4-31b-it-bf16`: Hosted locally via llama-swap. Requires llama.cpp b8665+ for the dedicated Gemma 4 tool call parser (PR #21418). Skipped by default; re-enable for llama-swap benchmark runs.
- `glm_4_7_flash_bf16` -> `ollama/glm/glm-4.7-flash-bf16`: Hosted locally via llama-swap. Needs --jinja --reasoning-format none to suppress <think> tags in content. Tool calling works correctly with these flags.
- `llama4_scout` -> `ollama/meta/llama4-scout`: Hosted locally via llama-swap. Skipped by default: llama.cpp has no parser for Llama 4's pythonic tool call format — model outputs tool calls as plain text content instead of structured tool_calls. Requires upstream llama.cpp support (similar to vLLM's llama4_pythonic parser).
- `qwen3_32b` -> `ollama/qwen/qwen3-32b`: Requested local model family; exact hosted variant available through opencode. Superseded by the Qwen 3.5 line for future local benchmarking. Skipped by default after benchmark preview averaged 7.96 output tok/s over the first 3 steps (< 20.00).
- `qwen3_coder_next` -> `ollama/qwen/qwen3-coder-next`: Best direct coding-oriented local Qwen variant matching the original benchmark brief. Skipped by default after benchmark preview measured 6.59 output tok/s (< 20.00).
- `qwen3_5_35b` -> `ollama/qwen/qwen3.5-35b`: Requested local model family; exact hosted variant available through opencode. Skipped by default because the current benchmark pass is restricted to OpenRouter models that previously completed successfully.
- `qwen3_6_35b` -> `ollama/qwen/qwen3.6-35b`: Qwen 3.6 35B-A3B (released 2026-04-15). Same qwen3_5_moe architecture as 3.5 (35B total / 3B active MoE). Q3_K_M ~16 GB — drop-in replacement for 3.5. Significant benchmark gains: SWE-bench 73.4 (was 70), Terminal-Bench 51.5 (was 40.5), MCPMark 37 (was 27). Has vision encoder. Same chat template and llama.cpp flags as 3.5.
- `qwen3_5_122b` -> `ollama/qwen/qwen3.5-122b`: Hosted locally via llama-swap. Needs --reasoning-format none on llama-server to avoid reasoning_content tokens that some clients mishandle. Tool calling works correctly with Qwen chat template.
- `gpt_oss_20b` -> `ollama/openai/gpt-oss-20b`: Added as a local Ollama GPT OSS baseline for later warmup and benchmark testing.
- `claude_opus_4_6` -> `openrouter/anthropic/claude-opus-4.6`: Exact requested cloud model.
- `claude_opus_4_7` -> `openrouter/anthropic/claude-opus-4.7`: Anthropic Claude Opus 4.7 on OpenRouter. Built for long-running async agents. Same pricing as 4.6: $5/M input, $25/M output. 1M context, 128K max output. Released 2026-04-16.
- `claude_opus_4_8` -> `openrouter/anthropic/claude-opus-4.8`: Anthropic Claude Opus 4.8 on OpenRouter. Direct successor to Opus 4.7 using the regular (non-fast) endpoint. 1M context, tool calling supported, $5/M input and $25/M output. Tests whether the 4.8 release keeps Opus 4.7's benchmark-leading RubyLLM correctness while improving speed or implementation discipline.
- `claude_fable_5` -> `openrouter/anthropic/claude-fable-5`: Anthropic Claude Fable 5 on OpenRouter (snapshot claude-5-fable-20260609, released 2026-06). New Claude 5-generation model. 1M context, tool calling supported, $10/M input and $50/M output — 2x Opus 4.x pricing. Tests whether the new generation improves on Opus 4.7/4.8's benchmark-leading RubyLLM correctness.
- `opencode_opus_glm` -> `openrouter/anthropic/claude-opus-4.7`: opencode multi-agent: Opus 4.7 primary + GLM 5.1 (Z.ai) coding subagent. Tests whether the cost-effective Chinese model handles coding when Opus plans. GLM 5.1 via Z.ai coding plan endpoint (subscription). Comparable to Claude Code's opus+sonnet variant but with a non-Anthropic coder.
- `opencode_opus_glm_forced` -> `openrouter/anthropic/claude-opus-4.7`: Forced-delegation variant of opencode_opus_glm. Runs with prompts/benchmark_prompt_forced_delegation.txt. Measures whether forcing the orchestrator pattern produces usable code via Opus (plan) + GLM 5.1 (execute) vs the free-choice version which didn't delegate at all.
- `opencode_opus_kimi_forced` -> `openrouter/anthropic/claude-opus-4.7`: Replacement for opencode_opus_glm_forced after Z.ai GLM 5.1 subagent stalled twice in the forced-delegation experiment. Kimi K2.6 was Tier A (87/100) in the solo benchmark vs GLM 5.1's Tier C (46/100), and both planner+subagent run through OpenRouter (no provider mixing latency). Runs with prompts/benchmark_prompt_forced_delegation.txt.
- `opencode_opus_qwen36plus_forced` -> `openrouter/anthropic/claude-opus-4.7`: Test the cheap-cloud-executor pairing: Opus plans, Qwen 3.6 Plus (Tier B 71/100 solo via OpenRouter free tier) executes. Same provider lane as planner so should not exhibit the cross-provider task-dispatch stall seen with GLM 5.1 (Z.ai) and local Qwen (llama-swap). Runs with prompts/benchmark_prompt_forced_delegation.txt.
- `opencode_opus_deepseek_forced` -> `openrouter/anthropic/claude-opus-4.7`: Test whether DeepSeek V4 Pro (solo Tier C 69/100 — Tier 1 code with Tier 3 deliverables) executes cleanly when Opus handles the planning/integration. Same OpenRouter provider lane to avoid the cross-provider task-dispatch stall. Runs with prompts/benchmark_prompt_forced_delegation.txt.
- `opencode_gpt55_qwen36plus_forced` -> `openrouter/openai/gpt-5.5`: Stress test: GPT 5.5 (typically Codex-only because OpenAI restricts tool calling on OpenRouter for GPT 5.x) as opencode planner with cheap Qwen executor. KNOWN RISK: GPT 5.5 may not tool-call on OpenRouter; if it can't, the run will fail with no Task dispatches and that itself is a useful finding. Runs with prompts/benchmark_prompt_forced_delegation.txt.
- `opencode_gpt55_deepseek_forced` -> `openrouter/openai/gpt-5.5`: Stress test: GPT 5.5 + DeepSeek V4 Pro both via OpenRouter. KNOWN RISK: GPT 5.5 may lack tool calling on OpenRouter, in which case no delegation will occur. Runs with prompts/benchmark_prompt_forced_delegation.txt.
- `opencode_opus_qwen_forced` -> `openrouter/anthropic/claude-opus-4.7`: Forced-delegation variant of opencode_opus_qwen. Most interesting test case: expensive cloud orchestrator + free local executor. If this produces working code it's the cheapest usable multi-agent configuration. Depends on llama-swap with qwen3.6:35b loaded.
- `opencode_opus_qwen` -> `openrouter/anthropic/claude-opus-4.7`: opencode multi-agent: Opus 4.7 primary (cloud) + Qwen 3.6 35B (local llama-swap) coding subagent. Tests the 'local hybrid' hypothesis — expensive cloud orchestrator with free local executor. Depends on llama-swap running with qwen3.6:35b loaded.
- `gpt_5_4_pro` -> `openrouter/openai/gpt-5.4-pro`: Chosen from the OpenRouter GPT 5.4 family as the largest and most coding-oriented variant. Skipped by default because it failed in the previous benchmark pass.
- `gpt_5_4_codex` -> `gpt-5.4`: GPT 5.4 via Codex CLI at xhigh reasoning effort. Tier 2: correct entry point (RubyLLM.chat + ask + response.content) but add_message uses keyword args instead of positional hash — crashes on multi-turn. ~$16/run (15x Claude). Polished architecture but wrong API calling convention.
- `gpt_5_5_codex` -> `gpt-5.5`: GPT 5.5 via Codex CLI at xhigh reasoning effort. Successor to GPT 5.4 — matches gpt_5_4_codex config exactly so the comparison measures model capability delta, not harness differences. Expected to produce similar ~$16/run cost band.
- `gpt_5_4_multi_balanced` -> `gpt-5.4`: Codex multi-agent: xhigh plans and orchestrates, medium/balanced handles coding. Tests whether GPT 5.4 at lower effort can execute well when the xhigh parent makes decisions. Comparison against gpt_5_4_codex (xhigh alone).
- `gpt_5_4_multi_balanced_forced` -> `gpt-5.4`: Forced-delegation variant of gpt_5_4_multi_balanced. Same config as the free-choice version — the only difference is the forcing prompt at prompts/benchmark_prompt_forced_delegation.txt. Measures whether forcing the orchestrator pattern changes output quality or cost on Codex's multi_agent feature.
- `gpt_5_4_multi_faster_forced` -> `gpt-5.4`: Forced-delegation variant of gpt_5_4_multi_faster. Compares against the free-choice version to isolate the effect of the forcing prompt.
- `gpt_5_4_multi_faster` -> `gpt-5.4`: Codex multi-agent: xhigh plans, low handles fast coding. Tests the 'cheap executor' hypothesis — whether minimal reasoning on the subagent is enough when the parent provides the plan.
- `kimi_k2_5` -> `openrouter/moonshotai/kimi-k2.5`: Chosen as the latest/highest Kimi variant listed by OpenRouter locally.
- `kimi_k2_6` -> `openrouter/moonshotai/kimi-k2.6`: Direct successor to K2.5. $0.74/$4.66 per M, 256K context, tool calling supported. Tests whether K2.6 fixes K2.5's Tier 3 hallucinations of RubyLLM add_message() and complete().
- `grok_4_3` -> `openrouter/x-ai/grok-4.3`: x.AI Grok 4.3 via OpenRouter. $1.25/$2.50 per M (mid-tier), 1M context, tool calling supported. First Grok variant in the benchmark — tests whether Grok's RubyLLM API recall is correct (real chat.ask path) or hits the same fluent-DSL/chat.complete hallucinations seen in some Tier B/C cloud models. Pricing positions it between Kimi K2.6 ($0.50/$2.50) and DeepSeek V4 Pro ($0.44/$0.87), well below Opus ($5/$25).
- `mimo_v2_5_pro` -> `openrouter/xiaomi/mimo-v2.5-pro`: Xiaomi's flagship coding model. $1/$3 per M, 1M context, tool calling supported. Brand-new family we haven't tested — competitive pricing with mid-tier Chinese models like Kimi and GLM.
- `glm_5` -> `openrouter/z-ai/glm-5`: Chosen as the latest/highest GLM variant listed by OpenRouter locally; this replaces the local GLM test. Skipped by default because it completed with errors in the previous benchmark pass.
- `qwen3_6_plus` -> `openrouter/qwen/qwen3.6-plus`: Added from OpenRouter cloud availability; chose the non-preview Qwen 3.6 Plus variant exposed locally. Skipped by default because it completed with errors in the previous benchmark pass.
- `qwen3_5_397b_cloud` -> `openrouter/qwen/qwen3.5-397b-a17b`: Added as the OpenRouter cloud Qwen 3.5 flagship under the requested qwen3.5:397b-cloud benchmark slot. Skipped by default because it stalled after completing validation steps and never emitted a terminal stop.
- `gemma4_31b_cloud` -> `openrouter/google/gemma-4-31b-it`: Google Gemma 4 31B IT BF16 served via Ollama's hosted cloud (https://ollama.com). Originally added to bypass the local llama.cpp parser bugs that caused infinite repetition loops on local Q3/Q8 GGUFs. Curl tests confirm the model itself works correctly for tool calling. **However, opencode benchmark runs hit HTTP 504 Gateway Timeout consistently around 20-24K total tokens of conversation history** — Cloudflare edge appears to enforce a ~100s per-request limit which 20K+ token prefill exceeds. Tried maxRetries:5 (didn't help — failures are consistent, not transient). Set limit.context:16384 to force opencode history trimming below the wall. Skipped by default until either Ollama Cloud raises the timeout or we test via Google's native Gemini API. Requires OLLAMA_API_KEY env var with Ollama Cloud subscription.
- `llama4_scout_cloud` -> `openrouter/meta-llama/llama-4-scout`: Added as the OpenRouter cloud Llama 4 Scout benchmark counterpart to the unusable local Scout path. Skipped by default because it does not currently resolve cleanly in this opencode build.
- `nemotron_3_super_cloud` -> `openrouter/nvidia/nemotron-3-super-120b-a12b`: Added as the closest OpenRouter cloud Nemotron line available after local Nemotron Cascade 2 proved unusable in this harness. Skipped by default because it still needs a clean first benchmark run.
- `minimax_m2_7` -> `openrouter/minimax/minimax-m2.7`: Chosen as the largest/latest MiniMax variant listed by OpenRouter locally.
- `minimax_m3` -> `openrouter/minimax/minimax-m3`: MiniMax M3 on OpenRouter. Direct successor to MiniMax M2.7. 1M context, tool calling supported, $0.30/M input and $1.20/M output. Tests whether the new MiniMax release fixes M2.7's RubyLLM batch-form hallucination and becomes a viable low-cost Rails/RubyLLM builder.
- `deepseek_v3_2` -> `openrouter/deepseek/deepseek-v3.2`: Latest DeepSeek model on OpenRouter. Input $0.26/M, output $0.38/M.
- `deepseek_v4_flash` -> `openrouter/deepseek/deepseek-v4-flash`: DeepSeek V4 Flash — budget-tier variant at $0.14/M input, $0.28/M output (cheaper than V3.2). 1M context. Tool calling supported via OpenRouter. Test whether V4 fixes the RubyLLM API hallucination that made V3.2 Tier 3. Phase 2 disabled: DeepSeek's thinking-mode API rejects replayed `reasoning_content` tokens from opencode's session continuation.
- `deepseek_v4_pro` -> `openrouter/deepseek/deepseek-v4-pro`: DeepSeek V4 Pro — premium variant at $1.74/M input, $3.48/M output. 1M context. Uses thinking mode by default which requires the client to echo reasoning_content on subsequent turns (opencode doesn't). reasoning=false tells opencode to treat it as a non-reasoning model so it won't extract/pass back reasoning_content.
- `step_3_5_flash` -> `openrouter/stepfun/step-3.5-flash`: StepFun Step 3.5 Flash on OpenRouter. Input $0.10/M, output $0.30/M.
- `claude_sonnet_4_6` -> `openrouter/anthropic/claude-sonnet-4.6`: Anthropic Claude Sonnet 4.6 on OpenRouter. Input $3.00/M, output $15.00/M.
- `gemini_3_1_pro` -> `openrouter/google/gemini-3.1-pro-preview`: Latest Google Gemini model with enhanced SWE performance and agentic reliability. Input $2.00/M, output $12.00/M.
- `grok_4_20` -> `openrouter/x-ai/grok-4.20`: xAI's latest flagship on OpenRouter. Fastest model in the benchmark (8 min) but produced architecturally broken code: bypassed RubyLLM with ruby-openai (only in dev/test group, NameError in prod), used format.turbo_stream without installing turbo-rails, RUBY_VERSION=4.0.2 Dockerfile bug. Tier 3 — broken core.
- `glm_5_1` -> `zai/glm-5.1`: Z.ai's latest flagship GLM model. Uses Z.ai coding plan endpoint at https://api.z.ai/api/coding/paas/v4 (NOT the general /api/paas/v4) — Lite subscription includes glm-5.1 only via the coding endpoint. Completed in 22 min with 24 tests, correct primary RubyLLM.chat/ask usage, but invented chat.user/chat.assistant for multi-turn history seeding (single-turn works, multi-turn crashes). Tier 2 — works with caveats.
- `qwen3_5_27b_claude` -> `ollama/qwen/qwen3.5-27b-claude`: Qwen 3.5 27B distilled from Claude 4.6 Opus reasoning traces (Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled). Tests whether Claude reasoning distillation transfers RubyLLM API correctness — most non-Anthropic models hallucinate the gem's API, so a Claude-distilled Qwen is an interesting natural experiment.
- `qwen2_5_coder_32b` -> `ollama/qwen/qwen2.5-coder-32b`: Most popular dedicated coder of the Qwen 2.5 generation. Sourced from Ollama (Q4_K_M ~19 GB). On NVIDIA 5090 fits with 64K context.
- `qwen3_coder_30b` -> `ollama/qwen/qwen3-coder-30b`: Qwen 3 dedicated coder variant (the regular 30B, not the 51 GB qwen3-coder-next-ctx). Direct comparison with the general qwen3:32b. Sourced from Ollama (Q4_K_M ~18 GB).
- `qwen3_5_27b_sushi_coder` -> `ollama/qwen/qwen3.5-27b-sushi-coder`: Qwen 3.5 27B fine-tuned via reinforcement learning on Codeforces problems (bigatuna/Qwen3.5-27b-Sushi-Coder-RL). Q4_K_M ~15 GB. Tests whether RL coding fine-tuning transfers correct RubyLLM API usage — direct comparison with the Claude reasoning distillation (qwen3.5:27b-claude) and the general qwen3.5:35b.
- `gemma4_31b_cloud` -> `ollama-cloud/gemma4-31b`: Google Gemma 4 31B IT BF16 served via Ollama's hosted cloud (https://ollama.com). Bypasses the local llama.cpp parser bugs that caused infinite repetition loops on local Q3/Q8 GGUFs. Tests whether Gemma 4 is actually capable for agentic tool calling when served by Google's full-precision infrastructure rather than crippled by quantization + parser regressions. Requires OLLAMA_API_KEY env var with an Ollama Cloud subscription.
- `gemma4_12b_mlx_bf16_local` -> `ollama/gemma4:12b-mlx-bf16`: Local Ollama profile (host 192.168.15.201). Smaller Gemma 4 (12B) but FULL-PRECISION BF16 in MLX (~24GB). Tests whether the earlier Gemma degeneracy (types_v2..v18 loop on nvfp4/Q4) was a quantization artifact rather than the model. Run with drop_thinking=false + output 16384.
- `qwen3_6_27b_mlx_local` -> `ollama/qwen3.6:27b-mlx`: Local Ollama profile (host 192.168.15.201). MLX build of Qwen 3.6 27B. Smaller sibling of the 35B (which reasoned too heavily and stalled). Run with drop_thinking=false + output 16384 (lessons from the 35B). Tests whether the smaller 3.6 sustains the agentic loop better.
- `qwen3_6_35b_mlx_local` -> `ollama/qwen3.6:35b-mlx`: Local Ollama profile (host 192.168.15.201). MLX build of Qwen 3.6 35B-A3B (MoE). Successor to qwen3.5:27b-mlx, which was the only local model to sustain the agentic loop on the Go brief (Tier 2). Tests whether 3.6 improves on it. enable_followup for the phase-2 chat proof via the Ollama fallback.
- `qwen3_5_27b_mlx_local` -> `ollama/qwen3.5:27b-mlx`: Local Ollama profile (host 192.168.15.201). MLX build of Qwen 3.5 27B installed on the local server. MoE (~3B active) — lightest/fastest of the local set, run first. Qwen 3.5 needs tool calling to work for the build agent.
- `gemma4_26b_mlx_local` -> `ollama/gemma4:26b-mlx`: Local Ollama profile (host 192.168.15.201). MLX build of Gemma 4 26B installed on the local server.
- `gemma4_26b_local` -> `ollama/gemma4:26b`: Local Ollama profile (host 192.168.15.201). Non-MLX Gemma 4 26B installed on the local server. Comparison point against the MLX build to measure the MLX runtime delta.
- `gemma4_latest_local` -> `ollama/gemma4:latest`: Local Ollama profile (host 192.168.15.201). The gemma4:latest tag installed on the local server.

## Ollama Warmup

Loaded from `results/ollama_warmup.json`.

Minimum useful context target: `32768`

| Model | Highest verified ctx | Recommendation |
| --- | ---: | --- |
| Gemma 4 31B | 131072 | keep in benchmark at 131072 |
| GLM 4.7 Flash BF16 | - | No warmup result recorded. |
| Llama 4 Scout | - | No warmup result recorded. |
| Qwen 3 32B | - | No warmup result recorded. |
| Qwen 3 Coder Next | - | No warmup result recorded. |
| Qwen 3.5 35B | - | No warmup result recorded. |
| Qwen 3.6 35B | - | No warmup result recorded. |
| Qwen 3.5 122B | - | No warmup result recorded. |
| GPT OSS 20B | - | No warmup result recorded. |
| Qwen 3.5 27B Claude Distilled | - | No warmup result recorded. |
| Qwen 2.5 Coder 32B | - | No warmup result recorded. |
| Qwen 3 Coder 30B | - | No warmup result recorded. |
| Qwen 3.5 27B Sushi Coder RL | - | No warmup result recorded. |
| Gemma 4 12B (MLX BF16, local) | - | No warmup result recorded. |
| Qwen 3.6 27B (MLX, local) | - | No warmup result recorded. |
| Qwen 3.6 35B (MLX, local) | - | No warmup result recorded. |
| Qwen 3.5 27B (MLX, local) | 32768 | keep in benchmark at 32768 |
| Gemma 4 26B (MLX, local) | 32768 | keep in benchmark at 32768 |
| Gemma 4 26B (local) | 32768 | keep in benchmark at 32768 |
| Gemma 4 (latest, local) | 32768 | keep in benchmark at 32768 |

## Results

| Model | Provider | Warmup ctx | Status | Elapsed (s) | Total tokens | Tok/s | Works? | Files | Notes |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | --- |
| Gemma 4 31B | ollama | 131072 | not_run | - | - | - | n/a | 0 | Run has not been executed yet. Warmup verified 131072 context. keep in benchmark at 131072. |
| GLM 4.7 Flash BF16 | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Llama 4 Scout | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3 32B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3 Coder Next | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.5 35B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.6 35B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.5 122B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT OSS 20B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Claude Opus 4.6 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Claude Opus 4.7 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Claude Opus 4.8 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Claude Fable 5 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + GLM 5.1 coder | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + GLM 5.1 coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + Kimi K2.6 coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + Qwen 3.6 Plus coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + DeepSeek V4 Pro coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode GPT 5.5 + Qwen 3.6 Plus coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode GPT 5.5 + DeepSeek V4 Pro coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + Qwen 3.6 local coder (FORCED delegation) | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| opencode Opus 4.7 + Qwen 3.6 local coder | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 Pro | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 xHigh (Codex) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.5 xHigh (Codex) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 xHigh + medium coder (Codex multi-agent) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 xHigh + medium coder (FORCED delegation) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 xHigh + low coder (FORCED delegation) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GPT 5.4 xHigh + low coder (Codex multi-agent) | codex | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Kimi K2.5 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Kimi K2.6 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Grok 4.3 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Xiaomi MiMo V2.5 Pro | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GLM 5 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.6 Plus | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.5 397B Cloud | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Gemma 4 31B Cloud | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Llama 4 Scout Cloud | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Nemotron 3 Super Cloud | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| MiniMax M2.7 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| MiniMax M3 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| DeepSeek V3.2 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| DeepSeek V4 Flash | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| DeepSeek V4 Pro | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Step 3.5 Flash | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Claude Sonnet 4.6 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Gemini 3.1 Pro | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Grok 4.20 | openrouter | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| GLM 5.1 | zai | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.5 27B Claude Distilled | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 2.5 Coder 32B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3 Coder 30B | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Qwen 3.5 27B Sushi Coder RL | ollama | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Gemma 4 31B (Ollama Cloud) | ollama-cloud | - | not_run | - | - | - | n/a | 0 | Run has not been executed yet. |
| Gemma 4 12B (MLX BF16, local) | ollama | - | completed_with_errors | 564.38 | 5676 | 47.21 | no | 3 | Exit code -15. Generated files do not resemble the requested Go project. |
| Qwen 3.6 27B (MLX, local) | ollama | - | completed_with_errors | 811.29 | 7597 | 36.27 | partial | 9 | Exit code -15. Some expected benchmark artifacts exist, but the scaffold looks incomplete. |
| Qwen 3.6 35B (MLX, local) | ollama | - | failed | 1350.90 | - | - | no | 4 | Generated files do not resemble the requested Go project. |
| Qwen 3.5 27B (MLX, local) | ollama | 32768 | completed_with_errors | 598.35 | 6673 | 26.11 | no | 3 | Exit code -15. Generated files do not resemble the requested Go project. Warmup verified 32768 context. keep in benchmark at 32768. |
| Gemma 4 26B (MLX, local) | ollama | 32768 | not_run | - | - | - | n/a | 0 | Run has not been executed yet. Warmup verified 32768 context. keep in benchmark at 32768. |
| Gemma 4 26B (local) | ollama | 32768 | not_run | - | - | - | n/a | 0 | Run has not been executed yet. Warmup verified 32768 context. keep in benchmark at 32768. |
| Gemma 4 (latest, local) | ollama | 32768 | not_run | - | - | - | n/a | 0 | Run has not been executed yet. Warmup verified 32768 context. keep in benchmark at 32768. |

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

