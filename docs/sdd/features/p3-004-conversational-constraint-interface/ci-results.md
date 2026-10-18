# CI results - p3-004-conversational-constraint-interface

Run at: 2026-10-18T11:05:00+08:00

| Check | Command | Result |
|---|---|---|
| test | `cd SystemCode && test -f remy/api/docs/API_doc.md && uv run --package remy-api pytest -q remy/api/tests/features/plan && uv run --package remy-workflows pytest -q remy/workflows/tests && uv run --package remy-app pytest -q remy/app/tests` | PASS |
| lint | `cd SystemCode && uv run --package remy-api ruff check remy/api/src/api/features/plan remy/api/tests/features/plan --select F,E9 && uv run --package remy-workflows ruff check remy/workflows/src remy/workflows/tests --select F,E9 && uv run --package remy-app ruff check remy/app/src remy/app/tests --select F,E9` | PASS |
| typecheck | `cd SystemCode && uv run --package remy-api mypy remy/api/src/api/features/plan --ignore-missing-imports && uv run --package remy-workflows mypy remy/workflows/src --ignore-missing-imports && uv run --package remy-app mypy remy/app/src --ignore-missing-imports` | PASS |
| lint-imports | `cd SystemCode && uv run lint-imports` | PASS |

OVERALL: PASS

## Output (last 40 lines each)

### test
```
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /mnt/g/2Study/5Master/NUS/0ISS/1Sem1/ISY5001_Intelligent_Reasoning_System/Practice_Module/Workshop-Project-Submission-2026-10-10-AIS/SystemCode/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
44 passed, 1 warning in 10.13s
..............................                                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8
  /mnt/g/2Study/5Master/NUS/0ISS/1Sem1/ISY5001_Intelligent_Reasoning_System/Practice_Module/Workshop-Project-Submission-2026-10-10-AIS/SystemCode/.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
30 passed, 1 warning in 2.81s
........................................                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/starlette/testclient.py:53
  /mnt/g/2Study/5Master/NUS/0ISS/1Sem1/ISY5001_Intelligent_Reasoning_System/Practice_Module/Workshop-Project-Submission-2026-10-10-AIS/SystemCode/.venv/lib/python3.12/site-packages/starlette/testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8
  /mnt/g/2Study/5Master/NUS/0ISS/1Sem1/ISY5001_Intelligent_Reasoning_System/Practice_Module/Workshop-Project-Submission-2026-10-10-AIS/SystemCode/.venv/lib/python3.12/site-packages/langgraph/cache/base/__init__.py:8: LangChainPendingDeprecationWarning: The default value of `allowed_objects` will change in a future version. Pass an explicit value (e.g., allowed_objects='messages' or allowed_objects='core') to suppress this warning.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
40 passed, 2 warnings in 12.10s
```

### lint
```
All checks passed!
All checks passed!
All checks passed!
```

### typecheck
```
remy/api/src/api/features/plan/filtering.py:193: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
remy/api/src/api/features/plan/service.py:187: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
remy/api/src/api/features/plan/service.py:476: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
remy/api/src/api/features/plan/service.py:477: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
Success: no issues found in 14 source files
Success: no issues found in 8 source files
Success: no issues found in 7 source files
```

### lint-imports
```

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘


---------
Contracts
---------

Analyzed 65 files, 121 dependencies.
------------------------------------

domain is a leaf KEPT
workflows does not depend on api KEPT
api does not depend on app KEPT
api does not depend on workflows KEPT

Contracts: 4 kept, 0 broken.
```

<!-- machine-generated by `sdd.py ci`; never hand-edited -->
