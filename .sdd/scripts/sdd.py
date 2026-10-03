#!/usr/bin/env python3
"""sdd.py -- agent-agnostic SDD harness CLI.

Two independent locations:
  * KIT location      -- where this script lives (templates/, prompts/, skills/).
                         Only `init` needs it.
  * PROJECT root      -- discovered by walking up from cwd for `.sdd/`.
                         Every command except `init` needs it.

Commands
  init <project>            scaffold docs/sdd/ and .sdd/ into a project
  hash <id>                 print spec / plan / tasks hashes
  state <id>                print state.json
  check                     verify hashes + stage gates for every feature
  gate <stage> <id> [--advance]   assert one feature may enter a stage
  loop <id> pass|fail       count an implementation loop; cap exits 2
  ci <id>                   run configured checks, write ci-results.md
  collision <phase>         write phase-reviews/<phase>-collisions.md

Layout assumed
  docs/sdd/features/<id>/spec.md        -- with optional ## Clarifications
  docs/sdd/features/<id>/plan.md        -- with ## Tasks and ## Revision notes
  docs/sdd/features/<id>/state.json     -- hashes + verdicts + history
  docs/sdd/roadmap.md                   -- phases embedded
  docs/sdd/phase-reviews/<phase>.md     -- includes retro subsection

Hash semantics
  spec_hash   spec.md with ## Clarifications removed
  plan_hash   plan.md with ## Tasks and ## Revision notes removed
  tasks_hash  ## Tasks section only, ignoring checkbox state

Config (sdd.json at project root, optional):
  {
    "checks": [{"name":"test","command":"pytest -q"}],
    "retries": 2,
    "loop_cap": 2
  }
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, datetime
from pathlib import Path

# ---------- locations ----------

_ROOT: Path | None = None
_KIT_OVERRIDE: Path | None = None   # set by cmd_init before dispatch


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default cwd) looking for a project with `.sdd/`."""
    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".sdd").is_dir():
            return candidate
    raise SystemExit(
        "error: no .sdd/ directory found in this or any parent directory.\n"
        "       run `sdd.py init <project>` from the kit to scaffold one, or\n"
        "       cd into a project that has already been initialised."
    )


def root() -> Path:
    global _ROOT
    if _ROOT is None:
        _ROOT = find_root()
    return _ROOT


def kit() -> Path:
    if _KIT_OVERRIDE is not None:
        return _KIT_OVERRIDE
    return root() / ".sdd"


def sdd() -> Path:
    return root() / "docs" / "sdd"


def features() -> Path:
    return sdd() / "features"


def phase_reviews() -> Path:
    return sdd() / "phase-reviews"


def templates() -> Path:
    return kit() / "templates"


# ---------- normalization & hashing ----------

def norm(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: list[str] = []
    for line in text.split("\n"):
        line = line.rstrip()
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(norm(text).encode()).hexdigest()[:16]


def strip_section(text: str, heading: str) -> str:
    """Remove a `## <heading>` section from markdown, including its body."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$.*?(?=^##\s|\Z)",
                  text, re.M | re.S)
    return text[:m.start()] + text[m.end():] if m else text


def get_section(text: str, heading: str) -> str:
    """Return the body of `## <heading>`, or '' if absent."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                  text, re.M | re.S)
    return m.group(1) if m else ""


def normalize_tasks(tasks_body: str) -> str:
    """Tasks section normalized for hashing.

    Checkbox state is deliberately ignored: `- [ ]` and `- [x]` hash the same,
    so ticking a box during Implement does not invalidate tasks_hash. Any other
    edit — reworded task, reordered tasks, added/removed task — does.
    """
    text = tasks_body.replace("[x]", "[ ]").replace("[X]", "[ ]")
    return text


def hashes(fdir: Path) -> dict[str, str]:
    h: dict[str, str] = {}
    spec = fdir / "spec.md"
    plan = fdir / "plan.md"
    if spec.exists():
        h["spec_hash"] = digest(strip_section(spec.read_text(), "Clarifications"))
    if plan.exists():
        p = plan.read_text()
        tasks_body = get_section(p, "Tasks")
        stripped = strip_section(strip_section(p, "Tasks"), "Revision notes")
        h["plan_hash"] = digest(stripped)
        if tasks_body.strip():
            h["tasks_hash"] = digest(normalize_tasks(tasks_body))
    return h


# ---------- state ----------

def feature_dir(fid: str) -> Path:
    d = features() / fid
    if not d.is_dir():
        raise SystemExit(f"error: no such feature: {fid}\n"
                         f"       expected {d}")
    return d


def load_state(fdir: Path) -> dict:
    f = fdir / "state.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save_state(fdir: Path, st: dict) -> None:
    st["updated_at"] = datetime.datetime.now().astimezone().isoformat(
        timespec="seconds")
    (fdir / "state.json").write_text(json.dumps(st, indent=2) + "\n")


def record_history(st: dict, event: str) -> None:
    st.setdefault("history", []).append({
        "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": event,
    })


def feature_dirs() -> list[Path]:
    f = features()
    return sorted(p for p in f.glob("*/") if p.is_dir()) if f.exists() else []


# ---------- config ----------

def load_config() -> dict:
    f = root() / "sdd.json"
    return json.loads(f.read_text()) if f.exists() else {}


# ---------- shared validation ----------

def validate(fdir: Path, st: dict) -> list[str]:
    """Hash drift + internal consistency. Used by check, gate, ci."""
    problems: list[str] = []
    cur = hashes(fdir)
    for key in ("spec_hash", "plan_hash", "tasks_hash"):
        if key in st and key in cur and st[key] != cur[key]:
            problems.append(
                f"{key} drift (state {st[key]} != file {cur[key]})")
        if key in st and key not in cur:
            problems.append(f"{key} present in state but artifact missing")
    return problems


# ---------- stage model ----------

STAGE_ENTERS: dict[str, set[str] | None] = {
    "constitution": None,   # project-level; not per-feature
    "roadmap":      None,   # project-level; not per-feature
    "specify":      {"proposed", "specified", "planned", "plan-approved",
                     "tasks-approved", "implemented", "ci-passed",
                     "reviewed"},
    "plan":         {"specified", "planned", "plan-approved"},
    "implement":    {"tasks-approved", "implemented", "ci-passed", "reviewed"},
    "review":       {"ci-passed", "reviewed"},
    "close":        {"reviewed", "closed"},
}

ADVANCE_TO = {
    "specify":   "specified",
    "plan":      "planned",
    "implement": "implemented",
    "review":    "reviewed",
    "close":     "closed",
}


# ---------- init ----------

def cmd_init(args: argparse.Namespace) -> int:
    global _KIT_OVERRIDE

    kit_root = Path(__file__).resolve().parent.parent
    if not (kit_root / "templates").is_dir():
        return _fail(f"templates not found at {kit_root / 'templates'}\n"
                     f"       expected a kit layout with templates/ beside "
                     f"scripts/")
    _KIT_OVERRIDE = kit_root

    project = Path(args.project).resolve()
    if not project.exists():
        return _fail(f"project path does not exist: {project}")
    if not project.is_dir():
        return _fail(f"project path is not a directory: {project}")

    dest = project / "docs" / "sdd"
    kit_dest = project / ".sdd"

    # 1. kit code + assets
    for sub in ("templates", "prompts", "skills", "scripts"):
        (kit_dest / sub).mkdir(parents=True, exist_ok=True)

    for t in (kit_root / "templates").glob("*"):
        if t.is_file():
            dst = kit_dest / "templates" / t.name
            if not dst.exists():
                dst.write_text(t.read_text())

    for sub in ("prompts", "skills"):
        src_dir = kit_root / sub
        if src_dir.is_dir():
            for f in src_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src_dir)
                    dst = kit_dest / sub / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        dst.write_text(f.read_text())

    self_dst = kit_dest / "scripts" / "sdd.py"
    if not self_dst.exists():
        self_dst.write_text(Path(__file__).read_text())

    # 2. SDD state dirs (no retros/ — retro lives inside phase-reviews/)
    for sub in ("features", "phase-reviews", "amendments"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    # 3. seed top-level artifacts (non-destructive)
    for name in ("proposal.md", "constitution.md", "roadmap.md"):
        src = kit_root / "templates" / name
        dst = dest / name
        if src.exists() and not dst.exists():
            dst.write_text(src.read_text())

    # 4. AGENTS.md at project root, never overwritten
    agents_src = kit_root / "templates" / "AGENTS.md"
    agents_dst = project / "AGENTS.md"
    if agents_src.exists() and not agents_dst.exists():
        agents_dst.write_text(agents_src.read_text())
    elif agents_dst.exists():
        print(f"note: {agents_dst} already exists — not overwritten")
        print(f"      merge the tooling block by hand if needed")

    print(f"scaffolded {dest}")
    print(f"kit copied to {kit_dest}")
    return 0


# ---------- hash / state ----------

def cmd_hash(args: argparse.Namespace) -> int:
    for k, v in hashes(feature_dir(args.feature)).items():
        print(f"{k}: {v}")
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    print(json.dumps(load_state(feature_dir(args.feature)), indent=2))
    return 0


# ---------- check ----------

def cmd_check(args: argparse.Namespace) -> int:
    failures = 0
    for fdir in feature_dirs():
        st = load_state(fdir)
        if not st:
            print(f"{fdir.name}: no state.json (skipped)")
            continue
        problems = validate(fdir, st)
        stage = st.get("stage", "")
        verdict = st.get("plan_review_verdict")

        if stage in ("plan-approved", "tasks-approved", "implemented",
                     "ci-passed", "reviewed", "closed"):
            if verdict not in ("APPROVE", "APPROVE-WITH-NITS"):
                problems.append(
                    f"stage {stage} but plan_review_verdict={verdict}")
        if stage in ("tasks-approved", "implemented", "ci-passed",
                     "reviewed", "closed") and "tasks_hash" not in st:
            problems.append(f"stage {stage} but tasks_hash missing")
        if stage in ("ci-passed", "reviewed", "closed") \
                and st.get("ci_overall") != "PASS":
            problems.append(
                f"stage {stage} but ci_overall={st.get('ci_overall')}")
        if stage in ("reviewed", "closed") \
                and st.get("review_verdict") != "APPROVE":
            problems.append(
                f"stage {stage} but review_verdict={st.get('review_verdict')}")
        if verdict in ("REVISE", "REJECT") and not st.get("override") \
                and stage in ("tasks-approved", "implemented", "ci-passed",
                              "reviewed", "closed"):
            problems.append(
                f"proceeded past {verdict} with no recorded override")

        if problems:
            failures += 1
            print(f"VIOLATION {fdir.name}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok {fdir.name} [{stage}]")
    print("STATE:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


# ---------- gate ----------

def cmd_gate(args: argparse.Namespace) -> int:
    stage = args.stage
    if STAGE_ENTERS.get(stage, "MISSING") is None:
        print(f"GATE {stage}: project-level (no per-feature state)")
        return 0

    fdir = feature_dir(args.feature)
    st = load_state(fdir)
    problems = validate(fdir, st)
    current = st.get("stage", "proposed")

    if current not in STAGE_ENTERS[stage]:
        allowed = ", ".join(sorted(STAGE_ENTERS[stage]))
        problems.append(
            f"stage is '{current}', gate '{stage}' requires one of: {allowed}")

    if stage == "implement":
        if "tasks_hash" not in st:
            problems.append("tasks_hash missing — tasks were never approved")
        if st.get("plan_review_verdict") in ("REVISE", "REJECT") \
                and not st.get("override"):
            problems.append(
                "plan review verdict blocks implement with no recorded override")
    if stage == "review":
        if st.get("ci_overall") not in ("PASS", "FAIL"):
            problems.append(
                f"ci_overall is {st.get('ci_overall')} — not conclusive")
    if stage == "close":
        if st.get("review_verdict") != "APPROVE":
            problems.append(
                f"review_verdict is {st.get('review_verdict')} — not APPROVE")

    if problems:
        print(f"GATE {stage} FAILED for {args.feature}")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"GATE {stage} PASSED for {args.feature}")
    if args.advance:
        new_stage = ADVANCE_TO.get(stage)
        if new_stage:
            st["stage"] = new_stage
            record_history(st, f"{current} -> {new_stage}")
            save_state(fdir, st)
            print(f"  advanced to {new_stage}")
    return 0


# ---------- loop ----------

def cmd_loop(args: argparse.Namespace) -> int:
    fdir = feature_dir(args.feature)
    st = load_state(fdir)
    cap = int(load_config().get("loop_cap", 2))
    if args.result == "fail":
        st["loops"] = int(st.get("loops", 0)) + 1
        record_history(st, f"loop {st['loops']}/{cap} (fail)")
        save_state(fdir, st)
        if st["loops"] >= cap:
            print(f"loop cap reached ({st['loops']}/{cap}) — human takes over")
            return 2
        print(f"loop {st['loops']}/{cap}")
    else:
        record_history(st, "loop pass")
        save_state(fdir, st)
        print(f"loop pass (count={st.get('loops', 0)}/{cap})")
    return 0


# ---------- ci ----------

INFRA_PAT = re.compile(
    r"(connection (refused|reset)|timed out|timeout|temporary failure|"
    r"could not resolve host|network is unreachable|registry|502 bad gateway|"
    r"no space left|rate limit)", re.I)

TAIL_LINES = 40


def run_once(cmd: str) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=3600)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except Exception as e:                       # noqa: BLE001
        return 125, str(e)


def tail(text: str, n: int = TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= n:
        return "\n".join(lines)
    return "\n".join([f"... ({len(lines) - n} lines omitted) ..."] +
                     lines[-n:])


def cmd_ci(args: argparse.Namespace) -> int:
    fdir = feature_dir(args.feature)
    cfg = load_config()
    checks = cfg.get("checks") or [{"name": "test", "command": "pytest"}]
    retries = int(cfg.get("retries", 2))
    rows: list[tuple[str, str, str]] = []
    outputs: list[tuple[str, str]] = []
    overall = "PASS"

    for c in checks:
        result, out = "FAIL", ""
        for _ in range(retries + 1):
            code, out = run_once(c["command"])
            if code == 0:
                result = "PASS"
                break
            if INFRA_PAT.search(out):
                result = "INCONCLUSIVE"
                continue
            result = "FAIL"
            break
        rows.append((c["name"], c["command"], result))
        outputs.append((c["name"], tail(out)))
        if result == "FAIL":
            overall = "FAIL"
        elif result == "INCONCLUSIVE" and overall == "PASS":
            overall = "INCONCLUSIVE"

    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    body = [f"# CI results - {fdir.name}", "", f"Run at: {ts}", "",
            "| Check | Command | Result |", "|---|---|---|"]
    body += [f"| {n} | `{c}` | {r} |" for n, c, r in rows]
    body += ["", f"OVERALL: {overall}", "",
             "## Output (last 40 lines each)", ""]
    for name, out in outputs:
        body.append(f"### {name}")
        body.append("```")
        body.append(out if out.strip() else "(no output)")
        body.append("```")
        body.append("")
    body.append("<!-- machine-generated by `sdd.py ci`; never hand-edited -->")
    body.append("")
    (fdir / "ci-results.md").write_text("\n".join(body))

    st = load_state(fdir)
    st["ci_overall"] = overall
    if overall == "PASS":
        st["stage"] = "ci-passed"
        record_history(st, "ci PASS")
    else:
        record_history(st, f"ci {overall}")
    save_state(fdir, st)
    print(f"OVERALL: {overall}  -> {fdir / 'ci-results.md'}")
    return 0 if overall == "PASS" else 1


# ---------- collision ----------

PATH_RE = re.compile(r"^\s*[-*]?\s*`?([\w./-]+\.[A-Za-z0-9]+)`?\s*$", re.M)
IDENT_RE = re.compile(r"`?(\w+)\(\)`?")


def plan_paths(plan_text: str) -> set[str]:
    return {m.group(1)
            for m in PATH_RE.finditer(get_section(plan_text, "Files to touch"))}


def plan_idents(plan_text: str) -> set[str]:
    return set(IDENT_RE.findall(get_section(plan_text, "Design")))


def cmd_collision(args: argparse.Namespace) -> int:
    phase = args.phase
    feats = [d for d in feature_dirs() if d.name.startswith(phase + "-")]
    files: dict[str, list[str]] = {}
    idents: dict[str, list[str]] = {}
    for d in feats:
        p = d / "plan.md"
        if not p.exists():
            continue
        t = p.read_text()
        for f in plan_paths(t):
            files.setdefault(f, []).append(d.name)
        for i in plan_idents(t):
            idents.setdefault(i, []).append(d.name)

    high = {f: v for f, v in files.items() if len(v) > 1}
    low = {i: v for i, v in idents.items()
           if len(v) > 1 and not any(i in f for f in high)}

    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"# Plan collision check - {phase}", "", f"Run at: {ts}", "",
             "| File | Features | Severity |", "|---|---|---|"]
    lines += [f"| {f} | {', '.join(v)} | HIGH |"
              for f, v in sorted(high.items())]
    lines += [f"| {i}() | {', '.join(v)} | LOW |"
              for i, v in sorted(low.items())]
    lines += ["", "## Detail", ""]
    for f in sorted(high):
        lines.append(f"### {f}")
        for n in high[f]:
            lines.append(f"- {n} plan touches this file.")
        lines.append("")
    lines += [f"OVERALL: {len(high)} collision(s), "
              f"{len(high)} blocker(s).", "",
              "HIGH collisions block Tasks approval until plans are amended "
              "or a human records an override in the affected features' "
              "decisions.md.", "",
              "<!-- machine-generated; never hand-edited -->", ""]

    phase_reviews().mkdir(parents=True, exist_ok=True)
    out = phase_reviews() / f"{phase}-collisions.md"
    out.write_text("\n".join(lines))
    print(f"{out}: {len(high)} HIGH, {len(low)} LOW")
    return 1 if high else 0


# ---------- helpers ----------

def _fail(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 2


# ---------- cli ----------

def main() -> int:
    ap = argparse.ArgumentParser(prog="sdd.py",
                                 description="agent-agnostic SDD harness")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="scaffold a project")
    p.add_argument("project", nargs="?", default=".")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("hash", help="print artifact hashes for one feature")
    p.add_argument("feature")
    p.set_defaults(fn=cmd_hash)

    p = sub.add_parser("state", help="print state.json for one feature")
    p.add_argument("feature")
    p.set_defaults(fn=cmd_state)

    p = sub.add_parser("check", help="verify all features' hashes and gates")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("gate", help="assert a feature may enter a stage")
    p.add_argument("stage",
                   choices=["constitution", "roadmap", "specify",
                            "plan", "implement", "review", "close"])
    p.add_argument("feature")
    p.add_argument("--advance", action="store_true",
                   help="advance stage on success")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("loop", help="count an implementation loop")
    p.add_argument("feature")
    p.add_argument("result", choices=["pass", "fail"])
    p.set_defaults(fn=cmd_loop)

    p = sub.add_parser("ci", help="run checks, write ci-results.md")
    p.add_argument("feature")
    p.set_defaults(fn=cmd_ci)

    p = sub.add_parser("collision", help="cross-feature plan collision check")
    p.add_argument("phase")
    p.set_defaults(fn=cmd_collision)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
