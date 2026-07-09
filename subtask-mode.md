# Subtask Mode (`--subtask-mode`)

## Problema

Modelos locais (Qwen 3.6 27B Dense, Qwen 3.6 35B A3B, Gemma 4 26B, etc.) **stallam** quando executam o prompt completo do benchmark em uma única sessão opencode.

Dois padrões de stalling foram observados:

1. **Repetição**: o modelo repete a mesma frase (ex: "Dispatching S3+S4") sem executar a ação
2. **Assistente mudo**: opencode mostra `assistant started` mas o modelo nunca completa a resposta

Isso acontece mesmo com contexto disponível (tokens totais bem abaixo do limite). O problema não é falta de memória ou contexto — é **acúmulo de complexidade multi-turn**. Modelos cloud (Claude, GPT) são robustos a isso; modelos locais não.

## Solução

O `--subtask-mode` separa a orquestração da execução:

| Camada | Responsabilidade | Implementado em |
|---|---|---|
| **Orquestrador** | Decompor o prompt, manter fila, passar contexto entre tasks | `decomposer.py` (Python puro — deterministico, zero stall) |
| **Executor** (LLM) | Pegar uma sub-tarefa focada e entregar | `run_opencode_phase()` — contexto fresco a cada task |

### Fluxo

```
┌─────────────────────────────────────────────────┐
│  Fase 0: Decompose                              │
│  Modelo lê o prompt do benchmark, escreve        │
│  subtasks.json com array de sub-tarefas          │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
              ┌───────┴───────┐
              │  Loop Python  │
              │  (decomposer) │
              └───────┬───────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   Sub-task 1    Sub-task 2    Sub-task 3
   (opencode     (opencode     (opencode
    session)      session)      session)
        │             │             │
        └─────────────┼─────────────┘
                      ▼
             Validação final
```

### Fase 0 — Decompose

O modelo recebe o `decompose_prompt.txt` que instrui:

> "Read the benchmark prompt and decompose into sub-tasks. Output ONLY subtasks.json."

Cada sub-tarefa deve ter:
  - `id`: identificador único (S1, S2, ...)
  - `description`: descrição auto-contida
  - `files`: lista de arquivos que cria/modifica
  - `dependencies`: lista de IDs de que depende
  - `acceptance_criteria`: critério de aceitação verificável

O modelo escreve `subtasks.json` no diretório do projeto. Se o decompose falhar (timeout/stall), o benchmark aborta — mas o decompose é uma tarefa leve (ler + escrever JSON), raramente stall.

### Loop de Execução

O Python ordena as tasks por dependência (topological sort) e executa cada uma:

1. Monta **prompt focado**: descrição da task + `ls -R` do projeto + critério de aceitação
2. Chama `run_opencode_phase` com esse prompt curto e **contexto fresco**
3. Se a task stall, só ela é perdida — as seguintes continuam
4. Ao final, `subtask-attempts.json` registra o status de cada task

## Como usar

```bash
# Com o modelo local + decomposição
python scripts/run_benchmark.py \
  --config config/models.mac.json \
  --model qwen3_6_27b_mlx \
  --prompt prompts/go/benchmark_prompt.txt \
  --followup-prompt prompts/go/benchmark_followup_prompt.txt \
  --local-backend llama-swap \
  --local-api-base http://192.168.15.201:8080 \
  --subtask-mode \
  --force
```

O modo standard (sem `--subtask-mode`) continua funcionando exatamente como antes — ideal para modelos cloud.

## Estrutura do Código

- `scripts/benchmark/decomposer.py`: toda a lógica (SubTask, decompose prompt, execução, coleta)
- `prompts/decompose_prompt.txt`: template do prompt de decomposição
- `scripts/run_benchmark.py`: adiciona `--subtask-mode` CLI flag

## Observado

- Modelos locais **conseguem fazer o decompose** (ler prompt + escrever JSON) sem stall — é uma tarefa cognitiva leve
- Cada sub-task individual é menor que o prompt completo — menos chance de stalling
- Se uma task stall, as seguintes continuam — degradação gradual, não falha catastrófica
- O custo total em tokens pode ser maior (cada task tem seu próprio prompt + contexto), mas o throughput é mais previsível
