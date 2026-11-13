# Verdictum AI — Baseline Backup & Recovery Specification

**Document:** `26_BASELINE_BACKUP_AND_RECOVERY.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** Baseline Protection, Database Snapshots & Recovery Verification  
**Status:** COMPLETE & VERIFIED  

---

## 1. Baseline Integrity Reference

Before modifying any source code, database schemas, or configurations, an immutable baseline reference was established:
- **Baseline Git Commit:** `f89058661605f6e80b2a59a93010b91e7ee55ec9`
- **Baseline Git Tag:** `verdictum-pre-rule-learning`
- **Description:** *"Verdictum AI — Stable Baseline Before Rule-Based Learning Implementation"*
- **Baseline Branch:** `main` (verified clean working tree)
- **Isolated Development Branch:** `feature/rule-learning-v1`

---

## 2. Database Backup & Preservation Protocol

### 2.1 SQLite Development Database Backup
```powershell
# Create timestamped snapshot of local database
Copy-Item -Path "backend\ai_verdict.db" -Destination "backend\ai_verdict.db.bak_pre_rule_learning_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

### 2.2 PostgreSQL Production Backup Command
```bash
# Executed on remote target host prior to applying any production migrations
pg_dump -U aiverdict_user -h 127.0.0.1 -p 5432 -F c -b -v -f "/opt/backups/ai_verdict_pre_rule_learning_$(date +%Y%m%d_%H%M%S).dump" ai_verdict
```

---

## 3. Recovery Verification

The baseline has been verified recoverable through Git references:
1. `git checkout verdictum-pre-rule-learning` restores the exact pre-modification source code.
2. In the event of a rollback, all new tables (`rule_learning_profiles`, etc.) are independent and non-destructive; older application versions ignore these tables safely without encountering SQL exceptions.

