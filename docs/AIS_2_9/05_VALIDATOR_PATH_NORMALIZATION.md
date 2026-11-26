# 05 — Safe Typed Executable Path & Same-Event NT-Volume Normalization

- Created `backend/app/services/evidence_path_normalizer.py` implementing deterministic Win32/NT path parsing without any global volume mapping or hardcoded incident IDs.
- Enabled `SAME_EVENT_CMDLINE_NT_VOLUME_CORROBORATED` solely when:
  1. Claim field & source record share exact `source_event_id`.
  2. Sibling `process.command_line` (or matching executable path field) on that same event contains a qualified DOS executable path (`C:\...`).
  3. Parent-child lineage does not conflict, executable basename matches, AND full multi-segment relative path after volume/drive root matches identically.
- Disabled weak substring fallback on executable path fields and emitted full `validation_audit_trail`.
