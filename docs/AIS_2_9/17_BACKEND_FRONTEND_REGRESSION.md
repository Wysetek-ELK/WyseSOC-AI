# 17 — Backend and Frontend Regression Verification

- **Backend pytest (`17 suites`, including `test_ais_2_9_remediation.py`)**: `113 passed in 60.02s` (`test_results/backend_pytest_17suites.txt`)
- **Frontend unit suites (`npm --prefix frontend test`, 16 `.mjs` files)**: `PASS (exit 0)` (`test_results/frontend_tests.txt`)
- **Frontend production build (`npm run build`)**: `PASS (exit 0, 32 routes)` locally and on Server 1 deployment
- **Frontend ESLint (`npm --prefix frontend run lint`)**: `FAIL (364 pre-existing errors, 258 pre-existing warnings; 0 new errors)` (`test_results/frontend_lint.txt`)
- **Python lint (`ruff check .`)**: `NOT VERIFIED` (`ruff` not installed)
