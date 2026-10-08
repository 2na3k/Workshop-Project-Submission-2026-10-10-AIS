# CI results - p2-002-cost-nutrition-calculation

Run at: 2026-10-07T21:16:29+08:00

| Check | Command | Result |
|---|---|---|
| test | `cd remy/api && uv run --package remy-api pytest -q tests/features/calculator` | PASS |
| lint | `cd remy/api && uv run --package remy-api ruff check src/api/features/calculator --select F,E9` | PASS |
| typecheck | `cd remy/api && uv run --package remy-api mypy src/api/features/calculator --ignore-missing-imports` | PASS |

OVERALL: PASS

## Output (last 40 lines each)

### test
```
........................................                                 [100%]
=============================== warnings summary ===============================
../../.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /mnt/g/2Study/5Master/NUS/0ISS/1Sem1/ISY5001_Intelligent_Reasoning_System/Practice_Module/Workshop-Project-Submission-2026-10-10-AIS/SystemCode/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
40 passed, 1 warning in 10.07s
```

### lint
```
All checks passed!
```

### typecheck
```
Success: no issues found in 16 source files
```
