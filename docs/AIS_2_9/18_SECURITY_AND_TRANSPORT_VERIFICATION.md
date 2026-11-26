# 18 — Security and Transport Verification

- **RBAC Negative Probes**: `True` unauthenticated blocked (`401`), `True` forged JWT blocked (`401`), invalid login HTTP `401` across all 9 sensitive endpoints.
- **UPLA Security Scanner**: `0` secret findings and `0` static security findings across 59 changed files.
- **Transport Note**: UAT benchmark traffic ran over authorized `http://13.204.214.64:8000/v1`; production customer telemetry requires private VPC peering or TLS proxy.
