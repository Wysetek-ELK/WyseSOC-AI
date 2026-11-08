# Report 11: Audit Log Tamper Resistance & HMAC Hardening (P4-REQ-09)

## 1. Compliance Mandate & Threat Model

In SOC environments, audit trails are subjected to regulatory scrutiny (SOC 2, ISO 27001, PCI DSS). An audit log must prove that:
1. Records have not been altered after insertion (e.g., an insider modifying an administrative decision or verdict override).
2. Records cannot be fabricated or injected without knowledge of the cryptographic secret.
3. Every operational event (login, prompt approval, policy mutation, incident evaluation, dry-run replay) is cryptographically signed.

---

## 2. HMAC-SHA256 Cryptographic Architecture

Phase 4 hardens `AuditService` in `backend/app/services/audit_service.py` with keyed **HMAC-SHA256** signatures:

```
+---------------------------------------------------------------------------------------------------+
|                                 AUDIT LOG SIGNATURE COMPUTATION                                   |
|                                                                                                   |
|   Payload String:                                                                                 |
|   "{user_id}|{action}|{resource_type}|{resource_id}|{created_at.isoformat()}|{sorted_json_details}" |
|                                                                                                   |
|                                                +                                                  |
|                                                                                                   |
|                                 Key: settings.AUDIT_SIGNING_KEY                                   |
|                                 (Minimum 32 bytes from environment)                               |
|                                                                                                   |
|                                                v                                                  |
|                                         HMAC-SHA256                                               |
|                                                v                                                  |
|                       Signature: "3f8e4d2a1b9c7e0f8a5d3c2b1e4f7a9c..."                            |
|                       Key Identifier: "hmac-sha256-v1"                                            |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Database Schema Binding

In Alembic revision `004_phase4_production_hardening`, the `audit_logs` table incorporates:
- `signature`: `VARCHAR(128)` — Hex-encoded HMAC-SHA256 signature.
- `key_id`: `VARCHAR(64)` — Algorithm version indicator (e.g. `hmac-sha256-v1`), facilitating future key rotation.

---

## 4. Tamper Detection & Integrity Verification (`verify_audit_integrity`)

`AuditService` provides continuous audit verification via `verify_audit_integrity()`:

```python
async def verify_audit_integrity(self, limit: int = 500) -> Dict[str, Any]:
    records = await self.db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit))
    tampered_ids = []
    
    for r in records:
        expected = compute_audit_signature(...)
        if not hmac.compare_digest(r.signature, expected):
            tampered_ids.append(r.id)

    return {
        "total_inspected": len(records),
        "tampered_count": len(tampered_ids),
        "tampered_ids": tampered_ids,
        "integrity_status": "VALID" if len(tampered_ids) == 0 else "TAMPER_DETECTED"
    }
```

### Safety Features:
- **Constant-Time Comparison:** Uses `hmac.compare_digest` to prevent timing attack side-channels.
- **Strict Canonical Serialization:** `json.dumps(details, sort_keys=True)` guarantees deterministic serialization regardless of key ordering in dictionaries.

---

## 5. Verification Evidence

Test module `backend/tests/test_backup_restore.py` validates:
- `test_audit_hmac_signature_and_tamper_detection`: PASSED.
  1. Creates authentic signed audit entries -> `verify_record()` returns `True`.
  2. Runs `verify_audit_integrity()` -> Reports `integrity_status = "VALID"`, `tampered_count = 0`.
  3. Modifies `record.action` in-place -> `verify_record()` immediately detects the tampering and returns `False`.

