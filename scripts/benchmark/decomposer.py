"""Sub-task decomposition: break a large benchmark prompt into sub-tasks and execute them in sequence.

When --subtask-mode is active, the benchmark replaces the single-phase run with:
  1. Decompose phase:  send the benchmark prompt to the model with instructions to
                        produce a decomposition JSON (subtasks.json).
  2. Execution loop:   for each sub-task, run a fresh opencode session with a focused
                        prompt containing only the sub-task's description + context.

This avoids the multi-turn context accumulation that causes local models to stall.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmark.config import BenchmarkConfig
from benchmark.runner import build_opencode_command, stream_process_output, parse_event_stream, extract_metrics
from benchmark.util import print_line, utc_now, format_value, save_json

DECOMPOSE_PROMPT_PATH = Path("prompts/decompose_prompt.txt")
SUBTASKS_FILENAME = "subtasks.json"
SUBTASK_ATTEMPTS_FILENAME = "subtask-attempts.json"
RECOMPOSE_FILENAME = "recompose.json"
DECOMPOSE_RETRY_LIMIT = 5


@dataclass
class SubTask:
    id: str
    description: str
    files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""


def _make_subtask_prompt(task: SubTask, project_dir: Path, completed: list[tuple[SubTask, dict[str, Any]]]) -> str:
    """Build a focused prompt for a single sub-task, with context from previous steps."""
    parts = [
        f"## Sub-task: {task.id}",
        "",
        task.description,
        "",
        f"Acceptance criteria: {task.acceptance_criteria}",
        "",
        "Files to create or modify:",
    ]
    for f in task.files:
        parts.append(f"  - {f}")
    parts.append("")

    # List completed context so the sub-agent knows what already exists
    if completed:
        parts.append("## Already completed")
        for t, p in completed:
            parts.append(f"  - {t.id}: {t.description}")
        parts.append("")

    # Add project structure snapshot so the sub-agent knows what exists
    parts.append("## Current project state")
    try:
        ls_output = _run_ls_recursive(project_dir)
        if ls_output:
            parts.append("```")
            parts.append(ls_output)
            parts.append("```")
        else:
            parts.append("(empty workspace)")
    except OSError:
        parts.append("(workspace not accessible yet)")

    parts.append("")
    parts.append(
        "Complete this sub-task using the available tools (Write, Edit, Bash). "
        "Do not modify files outside the listed paths without explicit need. "
        "Do not stop to ask questions. "
        "Do not produce a plan — just implement."
    )
    parts.append(
        f"When done, verify your own work against the acceptance criteria above. "
        f"If something fails, fix it and retry. "
        f"Only stop when the criteria are met or a hard blocker is identified."
    )
    return "\n".join(parts)


def _run_ls_recursive(directory: Path) -> str:
    """List all non-hidden files recursively, one per line."""
    if not directory.exists():
        return ""
    lines: list[str] = []
    for root, dirs, files in os.walk(str(directory)):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        rel = root_path.relative_to(directory) if root_path != directory else Path(".")
        for f in sorted(files):
            if f.startswith("."):
                continue
            lines.append(str(rel / f))
    return "\n".join(lines)


def load_subtasks(project_dir: Path) -> list[SubTask]:
    """Read subtasks.json from the project directory."""
    path = project_dir / SUBTASKS_FILENAME
    if not path.exists():
        print_line(f"[decomposer] subtasks.json not found at {path}")
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            print_line(f"[decomposer] subtasks.json is not a JSON array")
            return []
        tasks = []
        for item in data:
            tasks.append(SubTask(
                id=item.get("id", "?"),
                description=item.get("description", ""),
                files=item.get("files", []),
                dependencies=item.get("dependencies", []),
                acceptance_criteria=item.get("acceptance_criteria", ""),
            ))
        print_line(f"[decomposer] loaded {len(tasks)} sub-tasks from {path}")
        return tasks
    except (json.JSONDecodeError, OSError) as e:
        print_line(f"[decomposer] failed to parse subtasks.json: {e}")
        return []


def _build_decompose_prompt(benchmark_prompt_path: Path, project_dir: Path) -> str:
    """Build the decompose prompt, substituting template vars."""
    template = DECOMPOSE_PROMPT_PATH.read_text().strip()
    return template.format(
        benchmark_prompt_path=str(benchmark_prompt_path.resolve()),
        project_dir=str(project_dir.resolve()),
    )


def _build_recompose_prompt(
    project_dir: Path,
    completed_tasks: list[tuple[SubTask, dict[str, Any]]],
    failed_task: SubTask | None,
    failed_result: dict[str, Any] | None,
    remaining_task_ids: list[str],
    original_benchmark_prompt: str,
) -> str:
    """Build a prompt for re-decomposition after a subtask stalled.

    Includes the current project state, what was already built, what failed,
    and asks the model to re-decompose only the remaining work.
    """
    parts = [
        "## Re-decomposition required",
        "",
        "A previous decomposition of the benchmark prompt was partially executed, "
        "but one sub-task stalled. Re-decompose ONLY the remaining work.",
        "",
        "## Original benchmark prompt",
        "```",
        original_benchmark_prompt[:2000],
        "```",
        "",
        "## Completed sub-tasks",
    ]
    for task, result in completed_tasks:
        elapsed = result.get("elapsed_seconds", 0)
        parts.append(f"  - {task.id}: {task.description} (elapsed={elapsed:.0f}s)")

    if failed_task and failed_result:
        parts.extend([
            "",
            "## Sub-task that stalled",
            f"  - {failed_task.id}: {failed_task.description}",
            f"  - Stall reason: {failed_result.get('stall_reason', 'unknown')}",
            f"  - Files it was supposed to create: {failed_task.files}",
            f"  - Acceptance criteria: {failed_task.acceptance_criteria}",
        ])

    parts.extend([
        "",
        "## Remaining work to decompose",
        f"The following sub-task IDs need to be re-decomposed: {remaining_task_ids}",
        "Break them into smaller, more focused sub-tasks that each complete in under 3 minutes.",
        "Each sub-task must be self-contained and achievable in a single fresh session.",
        "",
        "## Current project state",
    ])
    try:
        ls_output = _run_ls_recursive(project_dir)
        if ls_output:
            parts.append("```")
            parts.append(ls_output)
            parts.append("```")
    except OSError:
        parts.append("(workspace not accessible)")

    parts.extend([
        "",
        "Output ONLY one file: write the re-decomposition as JSON to",
        f"{project_dir.resolve()}/{SUBTASKS_FILENAME}",
        "",
        "The JSON format is the same as the original decomposition:",
        '[{"id": "S5a", "description": "...", "files": [...], "dependencies": [...], "acceptance_criteria": "..."}]',
        "",
        "Rules:",
        "- Re-decompose ONLY the remaining tasks. Do not re-list completed ones.",
        "- Use IDs that do not conflict with existing completed sub-task IDs.",
        "- Target 2-4 sub-tasks per re-decompose, not more.",
        "- Each task must be achievable in under 3 minutes.",
        "- Do NOT implement any sub-task. Only write the JSON file.",
    ])
    return "\n".join(parts)


def _find_original_prompt_path(bench: BenchmarkConfig) -> Path:
    """Find the original benchmark prompt file used for this run."""
    candidates = [
        Path.cwd() / "prompts/go/benchmark_prompt.txt",
        Path.cwd() / "prompts/ruby/benchmark_prompt.txt",
        bench.results_dir.parent / "prompts" / "go" / "benchmark_prompt.txt",
        bench.results_dir.parent / "prompts" / "ruby" / "benchmark_prompt.txt",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _run_single_opencode(
    bench: BenchmarkConfig,
    model: dict[str, Any],
    model_slug: str,
    prompt: str,
    prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    project_dir: Path,
    phase_name: str,
    timeout_seconds: int | None = None,
    no_progress_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Run a single opencode phase and return structured result."""
    prompt_path.write_text(prompt)

    runner = bench.runner
    command = build_opencode_command(
        runner, model["id"], prompt,
        continue_session_id=None, project_dir=project_dir,
    )

    wall_start = time.monotonic()
    process_env = os.environ.copy()
    if bench.opencode_config_path is not None:
        process_env["OPENCODE_CONFIG"] = str(bench.opencode_config_path.resolve())
    process_env["OPENCODE_PERMISSION"] = json.dumps({
        "bash": {"*": "allow"}, "edit": {"*": "allow"}, "write": {"*": "allow"},
        "read": {"*": "allow"}, "glob": {"*": "allow"}, "grep": {"*": "allow"},
        "list": {"*": "allow"}, "task": {"*": "allow"}, "question": {"*": "allow"},
        "todowrite": {"*": "allow"}, "external_directory": {"*": "allow"},
    }, separators=(",", ":"))

    import subprocess

    # Trust any mise.toml in the project dir so mise/node resolution works in subprocess
    try:
        subprocess.run(
            ["mise", "trust", "--all"],
            cwd=project_dir, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass

    process = subprocess.Popen(
        command, cwd=project_dir, env=process_env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True, bufsize=1,
    )

    effective_timeout = timeout_seconds if timeout_seconds is not None else bench.timeout_seconds
    effective_no_progress = no_progress_timeout_seconds if no_progress_timeout_seconds is not None else bench.no_progress_timeout_seconds

    result = stream_process_output(
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        project_dir=project_dir,
        model_slug=f"{model_slug}/{phase_name}",
        backend=bench.backend,
        timeout_seconds=effective_timeout,
        no_progress_timeout_seconds=effective_no_progress,
        min_preview_output_tps=bench.min_preview_output_tps,
        min_preview_samples=bench.min_preview_samples,
    )

    wall_end = time.monotonic()
    events = parse_event_stream(result.stdout)
    metrics = extract_metrics(events)
    total_tokens = metrics["tokens"].get("total")
    elapsed_seconds = round(wall_end - wall_start, 2)

    if result.timed_out:
        status = "timeout"
    elif result.stalled:
        status = "failed"
    elif process.returncode == 0:
        status = "completed"
    else:
        status = "failed"

    return {
        "phase": phase_name,
        "elapsed_seconds": elapsed_seconds,
        "ended_at": utc_now(),
        "exit_code": process.returncode,
        "finish_reason": metrics["finish_reason"],
        "status": status,
        "stalled": result.stalled,
        "stall_reason": result.stall_reason,
        "timed_out": result.timed_out,
        "tokens": metrics["tokens"],
        "total_tokens": total_tokens,
        "command": command,
        "stderr_excerpt": result.stderr[:2000],
    }


def run_subtask_mode(
    model: dict[str, Any],
    bench: BenchmarkConfig,
    index: int,
    total: int,
) -> dict[str, Any]:
    """Run the model in sub-task decomposition mode."""
    from benchmark.runner import summarize_project

    model_slug = model["slug"]
    result_dir = bench.results_dir / model_slug
    project_dir = result_dir / "project"
    result_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    tasks: list[SubTask] = []
    phases: list[dict[str, Any]] = []
    started_at = utc_now()

    # ------ DECOMPOSE PHASE ------
    print_line(f"[{model_slug}] subtask-mode: decomposing benchmark prompt into sub-tasks")
    original_prompt_path = _find_original_prompt_path(bench)
    decompose_prompt = _build_decompose_prompt(original_prompt_path, project_dir)
    decompose_prompt_path = result_dir / "decompose-prompt.txt"
    decompose_stdout = result_dir / "decompose-opencode-output.ndjson"
    decompose_stderr = result_dir / "decompose-opencode-stderr.log"

    # Use a shorter timeout for decomposition — it's just reading + writing one JSON file
    decompose_result = _run_single_opencode(
        bench=bench, model=model, model_slug=model_slug,
        prompt=decompose_prompt,
        prompt_path=decompose_prompt_path,
        stdout_path=decompose_stdout,
        stderr_path=decompose_stderr,
        project_dir=project_dir,
        phase_name="decompose",
        timeout_seconds=600,       # 10 min max for decomposition
        no_progress_timeout_seconds=180,  # 3 min stall
    )
    phases.append(decompose_result)

    result_path = result_dir / "result.json"

    if decompose_result["status"] == "failed" or decompose_result["status"] == "timeout":
        print_line(f"[{model_slug}] decomposition failed: {decompose_result.get('stall_reason', 'unknown')}")
        result = _build_final_result(
            model, model_slug, phases, project_dir, bench, started_at,
            subtask_result_summary={"decompose_retries": 0, "error": "initial decompose failed"},
        )
        save_json(result_path, result)
        return result

    # Load sub-tasks from the decomposition
    tasks = load_subtasks(project_dir)
    if not tasks:
        print_line(f"[{model_slug}] no sub-tasks found, falling back to standard run")
        phases[0]["fallback_to_standard"] = True
        result = _build_final_result(
            model, model_slug, phases, project_dir, bench, started_at,
            subtask_result_summary={"decompose_retries": 0, "error": "no subtasks from decompose"},
        )
        save_json(result_path, result)
        return result

    # Sort tasks by dependency order (topological sort by insertion)
    ordered = _order_by_dependencies(tasks)
    print_line(f"[{model_slug}] execution order: {[t.id for t in ordered]}")

    # ------ EXECUTION LOOP (with re-decompose on stall) ------
    completed_tasks: list[tuple[SubTask, dict[str, Any]]] = []
    current_task_set = ordered[:]
    decompose_retry_count = 0
    cycle = 1

    while current_task_set and decompose_retry_count <= DECOMPOSE_RETRY_LIMIT:
        print_line(
            f"[{model_slug}] execute cycle {cycle}: "
            f"{len(current_task_set)} remaining, "
            f"{decompose_retry_count} re-decompose(s) so far"
        )

        stalled_in_this_cycle = False
        stalled_task = None
        stalled_result = None

        for task_index, task in enumerate(current_task_set, start=1):
            print_line(
                f"[{model_slug}/subtask] [{task_index}/{len(current_task_set)}] "
                f"{task.id}: {task.description[:80]}..."
            )

            subtask_prompt = _make_subtask_prompt(task, project_dir, completed_tasks)
            subtask_prompt_path = result_dir / f"subtask-{task.id}-prompt.txt"
            subtask_stdout = result_dir / f"subtask-{task.id}-output.ndjson"
            subtask_stderr = result_dir / f"subtask-{task.id}-stderr.log"

            phase_result = _run_single_opencode(
                bench=bench, model=model, model_slug=model_slug,
                prompt=subtask_prompt,
                prompt_path=subtask_prompt_path,
                stdout_path=subtask_stdout,
                stderr_path=subtask_stderr,
                project_dir=project_dir,
                phase_name=f"subtask-{task.id}",
                no_progress_timeout_seconds=240,
            )
            phases.append(phase_result)

            status = phase_result["status"]
            tokens = phase_result.get("total_tokens") or 0
            elapsed = phase_result.get("elapsed_seconds", 0)
            print_line(
                f"[{model_slug}/subtask] {task.id} status={status} "
                f"elapsed={elapsed:.1f}s tokens={format_value(tokens)}"
            )

            if status == "completed":
                completed_tasks.append((task, phase_result))
            elif status in ("failed", "timeout"):
                stalled_in_this_cycle = True
                stalled_task = task
                stalled_result = phase_result
                # Save attempt log up to this point
                _save_attempt_log(completed_tasks, result_dir)
                break

        if not stalled_in_this_cycle:
            # All tasks in this cycle completed — done
            break

        # A subtask stalled — try to re-decompose the remaining work
        completed_ids = {c[0].id for c in completed_tasks}
        remaining_ids = [t.id for t in current_task_set if t.id not in completed_ids]

        decompose_retry_count += 1
        if decompose_retry_count > DECOMPOSE_RETRY_LIMIT:
            print_line(
                f"[{model_slug}] re-decompose limit ({DECOMPOSE_RETRY_LIMIT}) reached, stopping"
            )
            break

        print_line(
            f"[{model_slug}] re-decompose attempt {decompose_retry_count}/{DECOMPOSE_RETRY_LIMIT}: "
            f"{stalled_task.id} stalled, re-decomposing remaining {remaining_ids}"
        )

        original_benchmark_text = bench.prompt
        recompose_prompt = _build_recompose_prompt(
            project_dir=project_dir,
            completed_tasks=completed_tasks,
            failed_task=stalled_task,
            failed_result=stalled_result,
            remaining_task_ids=remaining_ids,
            original_benchmark_prompt=original_benchmark_text,
        )
        recompose_prompt_path = result_dir / f"recompose-{decompose_retry_count}-prompt.txt"
        recompose_stdout = result_dir / f"recompose-{decompose_retry_count}-output.ndjson"
        recompose_stderr = result_dir / f"recompose-{decompose_retry_count}-stderr.log"

        recompose_result = _run_single_opencode(
            bench=bench, model=model, model_slug=model_slug,
            prompt=recompose_prompt,
            prompt_path=recompose_prompt_path,
            stdout_path=recompose_stdout,
            stderr_path=recompose_stderr,
            project_dir=project_dir,
            phase_name=f"recompose-{decompose_retry_count}",
            timeout_seconds=600,
            no_progress_timeout_seconds=180,
        )
        phases.append(recompose_result)

        if recompose_result["status"] in ("failed", "timeout"):
            print_line(
                f"[{model_slug}] re-decompose attempt {decompose_retry_count} also stalled, stopping"
            )
            break

        # Load the new decomposition
        new_tasks = load_subtasks(project_dir)
        if not new_tasks:
            print_line(f"[{model_slug}] re-decompose produced no tasks, stopping")
            break

        current_task_set = _order_by_dependencies(new_tasks)
        print_line(
            f"[{model_slug}] re-decompose produced {len(current_task_set)} new tasks: "
            f"{[t.id for t in current_task_set]}"
        )
        cycle += 1

    # Save final attempt log
    _save_attempt_log(completed_tasks, result_dir)

    result = _build_final_result(
        model, model_slug, phases, project_dir, bench, started_at,
        subtask_result_summary={
            "completed": len(completed_tasks),
            "decompose_retries": decompose_retry_count,
            "total_cycles": cycle,
        },
    )
    save_json(result_path, result)
    print_line(f"[{model_slug}] result saved to {result_path} status={result['status']}")
    return result


def _order_by_dependencies(tasks: list[SubTask]) -> list[SubTask]:
    """Topological sort of sub-tasks by dependencies."""
    task_map = {t.id: t for t in tasks}
    ordered: list[SubTask] = []
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        visited.add(task_id)
        task = task_map.get(task_id)
        if task:
            for dep in task.dependencies:
                visit(dep)
            ordered.append(task)

    for t in tasks:
        visit(t.id)
    return ordered


def _save_attempt_log(completed_tasks: list[tuple[SubTask, dict[str, Any]]], result_dir: Path) -> None:
    """Save the attempt log to disk."""
    path = result_dir / SUBTASK_ATTEMPTS_FILENAME
    path.write_text(json.dumps([
        {"id": t.id, "status": p["status"], "elapsed": p.get("elapsed_seconds", 0),
         "tokens": p.get("total_tokens")}
        for t, p in completed_tasks
    ], indent=2))


def _build_final_result(
    model: dict[str, Any],
    model_slug: str,
    phases: list[dict[str, Any]],
    project_dir: Path,
    bench: BenchmarkConfig,
    started_at: str,
    subtask_result_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate all phases into a final result dict matching the standard format."""
    from benchmark.runner import summarize_project

    total_elapsed = round(sum(float(p.get("elapsed_seconds") or 0.0) for p in phases), 2)

    # Count only subtask phases (not decompose/recompose phases)
    subtask_phases = [p for p in phases if p["phase"].startswith("subtask-")]
    completed_subtasks = [p for p in subtask_phases if p["status"] == "completed"]
    failed_subtasks = [p for p in subtask_phases if p["status"] in ("failed", "timeout")]

    # Determine overall status based on subtask completion only
    if len(failed_subtasks) == 0 and len(completed_subtasks) > 0:
        overall_status = "completed"
    elif len(completed_subtasks) > 0:
        overall_status = "completed_with_errors"
    elif any(p["status"] in ("failed", "timeout") for p in subtask_phases):
        overall_status = "failed"
    else:
        overall_status = "failed"

    last_phase = phases[-1] if phases else {}
    total_tokens = sum(p.get("total_tokens") or 0 for p in phases)

    summary = dict(subtask_result_summary or {})
    summary.update({
        "total_subtasks": len(subtask_phases),
        "completed_subtasks": len(completed_subtasks),
        "failed_subtasks": len(failed_subtasks),
        "total_phases": len(phases),
    })

    payload = {
        "phase": "subtask-mode",
        "assistant_output_excerpt": last_phase.get("assistant_output_excerpt", ""),
        "command": [],
        "elapsed_seconds": total_elapsed,
        "ended_at": utc_now(),
        "exit_code": last_phase.get("exit_code"),
        "finish_reason": last_phase.get("finish_reason"),
        "model": model,
        "opencode_session_id": None,
        "paths": {
            "project_dir": str(project_dir),
        },
        "project_summary": summarize_project(project_dir, bench.project_profile),
        "prompt_sha256": "",
        "started_at": started_at,
        "status": overall_status,
        "stalled": any(p.get("stalled") for p in phases),
        "stall_reason": next((p.get("stall_reason") for p in phases if p.get("stalled")), None),
        "timed_out": any(p.get("timed_out") for p in phases),
        "timeout_seconds": bench.timeout_seconds,
        "no_progress_timeout_seconds": bench.no_progress_timeout_seconds,
        "tokens": {"total": total_tokens, "input": 0, "output": 0},
        "tokens_per_second": round(total_tokens / total_elapsed, 2) if total_tokens and total_elapsed else None,
        "output_tokens_per_second": None,
        "phases": phases,
        "subtask_summary": summary,
    }
    return payload
