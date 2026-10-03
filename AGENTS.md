# AGENTS.md

Read by every agent at every stage. Persistent instruction layer.

## Operating principles

- The project's binding rules are in `docs/sdd/constitution.md`. Read it before
  producing or reviewing any artifact. It overrides convenience.
- `docs/sdd/roadmap.md` is context, not law. The constitution is law.
- Follow the artifact ownership table in `docs/workflow.md`. **Only the owner of a
  stage may write that stage's artifact.** Do not edit another stage's output.
- `ci-results.md`, `state.json`, and `*-collisions.md` are machine-generated.
  Never hand-edit them.
- During Implement: execute the Tasks as written. Do not change task wording,
  order, or scope, and do not redefine the Plan. If the Plan is wrong, stop and
  route a finding upstream.
- Every agent stage that produces or reviews an artifact takes this file as input.

## Pointers

- Binding rules: `docs/sdd/constitution.md`
- Current plan of record: `docs/sdd/roadmap.md`
- Change history of the roadmap: `docs/sdd/roadmap-log.md`

## Project tooling

Workspace packages are the members declared in the root `pyproject.toml`
(`remy/domain`, `remy/api`, `remy/workflows`, `remy/data-crawler`,
`remy/data-preparation`). Concrete per-feature commands are recorded in
`sdd.json` at the project root.

Template (substitute `<package-name>` and `<package-dir>` from [sdd.json](sdd.json)):

- test:      `uv run --package <package-name> pytest -q <package-dir>/tests`
- lint:      `uv run --package <package-name> ruff check <package-dir>`
- typecheck: `uv run --package <package-name> mypy <package-dir> --ignore-missing-imports`

For p1-001: `package-name=remy-data-preparation`, `package-dir=remy/data-preparation`.

## Running Python in `SystemCode/`

All Python under `SystemCode/` runs through `uv` inside WSL. Do not invoke
`python`, `python3`, `pip`, `pytest`, `mypy`, or `ruff` directly. Do not run
Python from PowerShell, cmd.exe, or a Windows-native shell.

Use `uv run --package <package-name> <command>` for anything that executes
Python. The package's dependencies are declared in its `pyproject.toml` and
resolved by `uv sync --all-packages`; running Python outside this environment
will not see those dependencies.

If you are an agent with shell access:
- Ensure you are in a WSL shell (bash, zsh, or sh). If the working directory
  looks like `/mnt/c/...` or `/mnt/g/...`, you are in WSL and on the correct
  path; if it looks like `C:\...`, you are not.
- `uv` is on `PATH` in WSL but not in PowerShell. If `uv` reports
  "command not found," you are in the wrong shell.
- All commands in the tooling section above assume WSL. Do not translate them
  to PowerShell or cmd.

If you cannot run in WSL, stop and report it rather than falling back to a
different shell. Running the checks in the wrong environment produces results
that don't match CI and invalidates the evidence.
