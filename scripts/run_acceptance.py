"""Acceptance run wrapper — persist JSON + Markdown + audit_log.

NOT atomic: if `verifier.render_markdown` raises after JSON is written, a
stranded JSON file may remain and the audit_log will lack a record. The
JSON-first write order means partial failures are detectable by comparing
acceptance/*.json against audit_log entries. For Task 0 of v0.1.1 this is
acceptable — render_markdown is a pure function over the payload dict and
its only failure modes (KeyError, AttributeError) indicate spec violations
the user should see surface as exceptions. Revisit if production runs see
silent loss.

v0.1.3 additions (Task 18, spec ref Section 3.3.1 reproducibility 锁定):
- ``save_run`` now accepts ``data_brief_hash`` and ``system_prompt_hash`` and
  injects a ``reproducibility`` block into the persisted payload (model_id,
  model_version, sampler_temperature, pipeline_version, run_name).
- Markdown render dispatches on ``payload['mode']`` so mode 0 (``data_first``)
  uses the dedicated 人话 renderer.
- CLI accepts ``--reproducibility-manifest`` (path to data_brief.json — the
  ``data_brief_hash`` is read from there) and ``--repeat N`` to write N
  separate runs (each with its own ``_run<i>`` suffix in the run_name).

Usage from SKILL.md acceptance protocol:
    from run_acceptance import save_run
    json_path, md_path = save_run(verified_payload, run_name="task_v0.1.3_dataonly_20260525_run1")
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
DEFAULT_OUT = _REPO_ROOT / "acceptance_runs"

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _read_json_file(path: Path) -> dict[str, Any]:
    """Read JSON written by Unix tools or Windows PowerShell UTF-8 defaults."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_run(
    payload: dict[str, Any],
    run_name: str,
    out_dir: Path = DEFAULT_OUT,
    data_brief_hash: str | None = None,
    system_prompt_hash: str | None = None,
) -> tuple[Path, Path]:
    """Persist a mentor-verified payload as both JSON and rendered Markdown.

    Also appends a summary record to audit_log (idempotent — uses
    payload['audit_log_id'] if present, else new_id()).

    v0.1.3: ``data_brief_hash`` and ``system_prompt_hash`` are injected into a
    ``reproducibility`` block on the payload BEFORE the JSON is written, so the
    saved JSON is the canonical record of which run was produced from which
    inputs by which model (Section 3.3.1).

    Markdown render dispatches on ``payload['mode']``: ``data_first`` uses
    ``verifier.render_markdown_mode_0`` (人话 renderer), everything else uses
    the v0.1 publication renderer.

    Returns: (json_path, md_path).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    import json
    import audit_log
    import verifier

    # Inject reproducibility block (idempotent — overwrites if rerun).
    payload["reproducibility"] = {
        "model_id": os.environ.get("CLAUDE_MODEL_ID", "unknown"),
        "model_version": os.environ.get("CLAUDE_MODEL_VERSION", "unknown"),
        "sampler_temperature": os.environ.get("CLAUDE_TEMPERATURE", "default"),
        "data_brief_hash": data_brief_hash or "",
        "system_prompt_hash": system_prompt_hash or "",
        "pipeline_version": "0.1.3",
        "run_name": run_name,
    }

    stamp = date.today().isoformat().replace("-", "")
    base = f"{run_name}_{stamp}" if stamp not in run_name else run_name
    json_path = out_dir / f"{base}.json"
    md_path = out_dir / f"{base}.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    mode = payload.get("mode", "")
    if mode == "data_first":
        md = verifier.render_markdown_mode_0(payload)
    else:
        md = verifier.render_markdown(payload)
    md_path.write_text(md, encoding="utf-8")

    audit_log.append({
        "type": "acceptance_run",
        "run_name": run_name,
        "audit_log_id": payload.get("audit_log_id"),
        "mode": payload.get("mode"),
        "claims_count": len(payload.get("claims", [])),
        "json_path": str(json_path),
        "md_path": str(md_path),
    })

    return json_path, md_path


def _compute_prompt_hash() -> str:
    """SHA256 (first 16 hex) of installed SKILL.md (system prompt fingerprint).

    Checks two locations in order:
      1. <repo_root>/SKILL.md (when running from a checkout)
      2. ~/.claude/skills/thermal-mentor/SKILL.md (when installed as a skill)

    Returns 'skill_md_not_found' sentinel if neither exists, so the
    reproducibility block always has a defined value.
    """
    import hashlib
    candidates = [
        _REPO_ROOT / "SKILL.md",
        Path.home() / ".claude" / "skills" / "thermal-mentor" / "SKILL.md",
    ]
    for skill_md in candidates:
        if skill_md.exists():
            return hashlib.sha256(skill_md.read_bytes()).hexdigest()[:16]
    return "skill_md_not_found"


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("payload_json")
    p.add_argument(
        "--mode",
        default=None,
        help="data_first / novelty_review / etc — auto-detected from payload if None",
    )
    p.add_argument(
        "--reproducibility-manifest",
        type=Path,
        default=None,
        help="Path to data_brief.json (shared across N=3 reruns); "
        "data_brief_hash is read from this manifest.",
    )
    p.add_argument("--run-name", required=True)
    p.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat N times (each as separate run with _run<i> suffix).",
    )
    args = p.parse_args()

    data_brief_hash = ""
    if args.reproducibility_manifest:
        try:
            brief = _read_json_file(args.reproducibility_manifest)
        except FileNotFoundError:
            print(
                f"[error] --reproducibility-manifest path does not exist: "
                f"{args.reproducibility_manifest}",
                file=sys.stderr,
            )
            sys.exit(2)
        except json.JSONDecodeError as e:
            print(
                f"[error] --reproducibility-manifest is not valid JSON: "
                f"{args.reproducibility_manifest}\n  parse error at "
                f"line {e.lineno} col {e.colno}: {e.msg}",
                file=sys.stderr,
            )
            sys.exit(2)
        data_brief_hash = brief.get("data_brief_hash", "")

    system_prompt_hash = _compute_prompt_hash()

    try:
        payload = _read_json_file(Path(args.payload_json))
    except FileNotFoundError:
        print(
            f"[error] payload_json path does not exist: {args.payload_json}",
            file=sys.stderr,
        )
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(
            f"[error] payload_json is not valid JSON: {args.payload_json}\n"
            f"  parse error at line {e.lineno} col {e.colno}: {e.msg}",
            file=sys.stderr,
        )
        sys.exit(2)

    for n in range(1, args.repeat + 1):
        run_name = args.run_name if args.repeat == 1 else f"{args.run_name}_run{n}"
        json_path, md_path = save_run(
            payload,
            run_name=run_name,
            data_brief_hash=data_brief_hash,
            system_prompt_hash=system_prompt_hash,
        )
        print(f"[saved {n}/{args.repeat}] JSON: {json_path}")
        print(f"[saved {n}/{args.repeat}] Markdown: {md_path}")


if __name__ == "__main__":
    main()
