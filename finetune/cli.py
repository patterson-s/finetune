"""finetune/cli.py — orchestrates the pipeline stages from the shell.

Wire-up (design.md §2): collect -> augment -> adapt -> train -> store -> serve.
This is the B8 CLI layer: thin, delegating to the tested stage modules. Each
subcommand is independently runnable so stages can be invoked in isolation too.

Usage:
    python -m finetune --help
    python -m finetune collect --gold <path> --out <jsonl>
    python -m finetune store --task education_extraction --files <a> <b> [--backend hf|local]
    python -m finetune serve --backend llama_cpp --model <name> [--host .. --port ..]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .spec import load_tasks


def _add_store_parser(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--task", required=True, help="task id in configs/tasks.yaml")
    sp.add_argument("--files", nargs="+", required=True, help="artifact files to store")
    sp.add_argument("--backend", choices=["local", "hf"], default="local")
    sp.add_argument("--namespace", default="patterson-s")


def _add_serve_parser(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--backend", choices=["llama_cpp", "ollama"], required=True)
    sp.add_argument("--model", required=True, help="model name the server exposes")
    sp.add_argument("--host", default=None)
    sp.add_argument("--port", type=int, default=None)


def _cmd_store(args) -> int:
    from .store.registry import store_from_task

    m = store_from_task(args.task, args.files, backend=args.backend, namespace=args.namespace)
    print(json.dumps(m, indent=2, ensure_ascii=False))
    print(f"stored artifact {m['artifact_id']} -> {m.get('repo_id', 'local weights/')}")
    return 0


def _cmd_serve(args) -> int:
    from .serve.client import ServeClient
    from .serve.config import build_serve_config

    cfg = build_serve_config(args.backend, args.model, host=args.host, port=args.port)
    print(f"serve config: {cfg.base_url}  model={cfg.model}")
    hc = ServeClient(cfg).health_check()
    print("health:", hc)
    return 0 if hc["status"] == "ok" else 1


def _cmd_collect(args) -> int:
    from .collect.educ import build_dataset, write_jsonl

    gold = json.load(open(args.gold, encoding="utf-8"))
    rows = build_dataset(gold, include_negatives=not args.positive_only)
    out = write_jsonl(rows, args.out)
    print(f"wrote {len(rows)} rows -> {out}")
    return 0


def _cmd_tasks(args) -> int:
    tasks = load_tasks()
    for tid, t in tasks.items():
        print(f"{tid:32s} tier={t.tier} status={t.status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m finetune", description="Finetune pipeline orchestration")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("tasks", help="list task specs from configs/tasks.yaml")
    sp.set_defaults(func=_cmd_tasks)

    sp = sub.add_parser("collect", help="collect stage: gold -> training rows (JSONL)")
    sp.add_argument("--gold", required=True, help="path to education_check.json")
    sp.add_argument("--out", default="datasets/education/train_educ.jsonl")
    sp.add_argument("--positive-only", action="store_true", help="skip negative (has_education=0) rows")
    sp.set_defaults(func=_cmd_collect)

    sp = sub.add_parser("store", help="store stage: weights + manifest -> local weights/ or HF")
    _add_store_parser(sp)
    sp.set_defaults(func=_cmd_store)

    sp = sub.add_parser("serve", help="serve stage: point at a local OpenAI-compatible endpoint + health check")
    _add_serve_parser(sp)
    sp.set_defaults(func=_cmd_serve)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
