# 12 — Server 1 Deployment & Live Verification

- **UPLA Execution**: `upla-20261125-023922-feb3fd` (`COMPLETED_FULL_WORKFLOW`)
- **Deployed SHA**: `dfe4e6e59aefddd29347f3103c5c59832e386e9f` (verified on `server-1` `172.26.41.240`, `/opt/wysesoc-ai`)
- **Remote Steps Passed**: SSH preflight -> SHA backup -> checkout `dfe4e6e59aefddd29347f3103c5c59832e386e9f` -> `alembic upgrade head` -> remote pytest gate -> `npm run build` -> systemd restart -> live HTTP checks:
  - `GET http://172.26.41.240/api/health` -> `200 OK` (`postgresql` latency `2.56ms`)
  - `GET http://172.26.41.240/human-review-queue` -> `200 OK` (`49000` bytes)
  - `GET http://172.26.41.240/api/ground-truth/cohorts` -> `401 Unauthorized` (route mounted & auth-enforced)
- **Interactive Authenticated Browser Screenshots**: `NOT VERIFIED` (Chrome DevTools remote debugging `DevToolsActivePort` disabled on local workstation; operator approved proceeding to closeout).
