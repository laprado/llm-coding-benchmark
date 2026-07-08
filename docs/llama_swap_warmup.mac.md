# llama-swap Warmup Report

Generated at: 2026-06-22T16:44:09+00:00
API base: `http://192.168.15.201:8080`
Config: `config/models.mac.json`

| Slug | llama-swap model | Status | Elapsed (s) | Preflight tok/s | Notes |
| --- | --- | --- | ---: | ---: | --- |
| gemma4_26b_mlx | mlm-gemma-4-26B-A4B-it-OptiQ-4bit | ok | 7.3 | — | preload ok |
| gemma4_26b_ollama | olm-gemma4:26b-mlx | ok | 5.1 | — | preload ok |
| gemma4_26b_gguf | clm-gemma-4-26B-A4B-it | ok | 15.8 | 56.9 | preload ok (56.9 tok/s) |
| qwen3_6_35b_a3b_gguf | clm-qwen3.6-35b-a3b | ok | 16.6 | 69.2 | preload ok (69.2 tok/s) |
| qwen3_5_35b_a3b_coding_mlx | olm-qwen3.5:35b-a3b-coding-nvfp4 | ok | 7.8 | — | preload ok |
