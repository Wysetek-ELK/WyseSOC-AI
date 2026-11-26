"""Typed Evidence & Path Normalization Engine (AIS 2.9 Workstream C).

Provides strict, provenance-preserving normalization for Windows DOS drive paths,
NT device paths (`\\Device\\HarddiskVolumeN\\...`), UNC paths, POSIX paths, and
quoted/escaped command-line executables without filename-only matching or
unverified global NT-device volume assumptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.canonical_evidence import CanonicalEvidenceRecord

PATH_FIELD_NAMES = frozenset({
    "process.file_path",
    "process.image_path",
    "process.executable_path",
    "process.path",
    "process.command_line",
    "process.cmdline",
    "cmdline",
    "process.parent_command_line",
    "process.parent_file_path",
    "file.path",
    "target_filepath",
})

CHILD_PROCESS_PATH_FIELDS = frozenset({
    "process.file_path",
    "process.image_path",
    "process.executable_path",
    "process.path",
    "process.command_line",
    "process.cmdline",
    "cmdline",
})

PARENT_PROCESS_PATH_FIELDS = frozenset({
    "process.parent_command_line",
    "process.parent_file_path",
})

_NT_DEVICE_RE = re.compile(r"^\\device\\(harddiskvolume\d+)(\\.*)$", re.IGNORECASE)
_EXTENDED_DOS_RE = re.compile(r"^(?:\\\\\?\\|\\\?\?\\)([A-Za-z]:\\.*)$")
_DOS_DRIVE_RE = re.compile(r"^([A-Za-z]:)(\\.*)$")
_UNC_RE = re.compile(r"^(\\\\[^\\]+\\[^\\]+)(\\.*)?$")
_EXEC_EXT_RE = re.compile(
    r"^(.*?\.(?:exe|dll|ps1|bat|cmd|com|msi|vbs|js|py))(?:\s|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NormalizedPathResult:
    original: str
    normalized: str
    namespace: str  # DOS_DRIVE | NT_DEVICE_VOLUME | UNC | POSIX | RELATIVE
    drive_or_volume: Optional[str]
    relative_path: str
    basename: str
    is_windows: bool
    extracted_from_cmdline: bool


def is_path_field(field_name: Optional[str]) -> bool:
    f = str(field_name or "").strip().lower()
    if f in PATH_FIELD_NAMES:
        return True
    return f.endswith(("_file_path", "_image_path", "_command_line", "_executable_path", ".file_path", ".image_path"))


def looks_like_path_value(val: Any) -> bool:
    s = str(val or "").strip()
    if len(s) < 3:
        return False
    return (
        s.startswith(("\\Device\\", "\\\\?\\", "\\??\\", "\\\\", "/"))
        or bool(re.match(r'^"?[A-Za-z]:[\\/]', s))
    )


def _strip_wrapping_quotes(s: str) -> str:
    val = s.strip()
    while len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
        val = val[1:-1].strip()
    return val


def extract_command_line_executable(cmdline: str) -> str:
    """Extracts ONLY the primary executable token from a command line (ignores arguments)."""
    s = cmdline.strip()
    # Normalize JSON-escaped quotes/slashes gently if raw string leaked
    while "\\\\" in s:
        s = s.replace("\\\\", "\\")
    s = s.strip()
    if s.startswith('"'):
        end_idx = s.find('"', 1)
        if end_idx > 1:
            return s[1:end_idx].strip()
    if s.startswith("'"):
        end_idx = s.find("'", 1)
        if end_idx > 1:
            return s[1:end_idx].strip()
    ext_match = _EXEC_EXT_RE.match(s)
    if ext_match:
        return ext_match.group(1).strip()
    return s.split()[0] if s.split() else s


def normalize_executable_path(raw: Any, from_cmdline: bool = False) -> Optional[NormalizedPathResult]:
    """Parses and canonically normalizes a Windows/NT/UNC/POSIX file or command-line executable path."""
    if raw is None:
        return None
    orig = str(raw).strip()
    if not orig:
        return None

    candidate = orig
    # Unescape JSON-doubled backslashes when comparing asserted strings vs raw telemetry
    while "\\\\" in candidate:
        # Preserve UNC double-leading backslash only if strictly at index 0 followed by non-backslash host
        if candidate.startswith("\\\\") and not candidate.startswith("\\\\?\\") and "\\\\" not in candidate[2:]:
            break
        candidate = re.sub(r"(?<!^)\\\\", r"\\", candidate)
        if candidate.startswith("\\\\") and candidate.count("\\\\") > 1:
            candidate = candidate.replace("\\\\", "\\")
        elif candidate.startswith("\\\\") and ":" in candidate[:8]:
            # `"C:\\Program Files..."` style
            candidate = candidate.replace("\\\\", "\\")
        elif "\\\\" in candidate and not _UNC_RE.match(candidate):
            candidate = candidate.replace("\\\\", "\\")

    if from_cmdline:
        candidate = extract_command_line_executable(candidate)
    else:
        candidate = _strip_wrapping_quotes(candidate)
        # Handle if a model passed a quoted path with trailing arguments on file_path
        if " " in candidate and re.search(r"\.(?:exe|dll|ps1|bat|cmd|com|msi)\s+", candidate, re.IGNORECASE):
            return None  # Reject arguments injected into an asserted exact file_path claim!

    if not candidate:
        return None

    # Standardize extended prefixes (`\??\C:\...`, `\\?\C:\...`)
    ext_m = _EXTENDED_DOS_RE.match(candidate)
    if ext_m:
        candidate = ext_m.group(1)

    # Collapse repeated internal backslashes (keep leading UNC \\ if applicable)
    if candidate.startswith("\\\\"):
        tail = re.sub(r"[\\/]+", r"\\", candidate[2:])
        win_cand = "\\\\" + tail
    else:
        win_cand = re.sub(r"[\\/]+", r"\\", candidate) if ("\\" in candidate or re.match(r"^[A-Za-z]:", candidate)) else candidate

    nt_m = _NT_DEVICE_RE.match(win_cand)
    if nt_m:
        vol = nt_m.group(1).lower()
        rel = nt_m.group(2).lower()
        norm = f"\\device\\{vol}{rel}"
        base = rel.rsplit("\\", 1)[-1]
        return NormalizedPathResult(
            original=orig,
            normalized=norm,
            namespace="NT_DEVICE_VOLUME",
            drive_or_volume=vol,
            relative_path=rel,
            basename=base,
            is_windows=True,
            extracted_from_cmdline=from_cmdline,
        )

    dos_m = _DOS_DRIVE_RE.match(win_cand)
    if dos_m:
        drv = dos_m.group(1).lower()
        rel = dos_m.group(2).lower()
        norm = f"{drv}{rel}"
        base = rel.rsplit("\\", 1)[-1]
        return NormalizedPathResult(
            original=orig,
            normalized=norm,
            namespace="DOS_DRIVE",
            drive_or_volume=drv,
            relative_path=rel,
            basename=base,
            is_windows=True,
            extracted_from_cmdline=from_cmdline,
        )

    unc_m = _UNC_RE.match(win_cand)
    if unc_m:
        root = unc_m.group(1).lower()
        rel = (unc_m.group(2) or "").lower()
        base = (rel or root).rsplit("\\", 1)[-1]
        return NormalizedPathResult(
            original=orig,
            normalized=f"{root}{rel}",
            namespace="UNC",
            drive_or_volume=root,
            relative_path=rel,
            basename=base,
            is_windows=True,
            extracted_from_cmdline=from_cmdline,
        )

    if candidate.startswith("/"):
        posix = re.sub(r"/+", "/", candidate)
        base = posix.rsplit("/", 1)[-1]
        return NormalizedPathResult(
            original=orig,
            normalized=posix,
            namespace="POSIX",
            drive_or_volume="/",
            relative_path=posix,
            basename=base,
            is_windows=False,
            extracted_from_cmdline=from_cmdline,
        )

    # Bare relative name / command
    is_win = "\\" in win_cand
    norm_rel = win_cand.lower() if is_win else candidate
    base = norm_rel.rsplit("\\" if is_win else "/", 1)[-1]
    return NormalizedPathResult(
        original=orig,
        normalized=norm_rel,
        namespace="RELATIVE",
        drive_or_volume=None,
        relative_path=norm_rel,
        basename=base,
        is_windows=is_win,
        extracted_from_cmdline=from_cmdline,
    )


def compare_paths_strict(
    asserted_raw: Any,
    observed_raw: Any,
    *,
    claim_field: str = "",
    obs_field: str = "",
) -> Tuple[bool, str, Optional[NormalizedPathResult], Optional[NormalizedPathResult]]:
    """Checks direct typed path equivalence without unsafe suffix or blind NT-volume assumptions."""
    c_is_cmd = "command_line" in claim_field.lower() or "cmdline" in claim_field.lower()
    o_is_cmd = "command_line" in obs_field.lower() or "cmdline" in obs_field.lower()

    na = normalize_executable_path(asserted_raw, from_cmdline=c_is_cmd)
    no = normalize_executable_path(observed_raw, from_cmdline=o_is_cmd)
    if not na or not no:
        return False, "UNPARSEABLE_PATH", na, no

    if na.namespace == no.namespace:
        if na.normalized == no.normalized:
            return True, f"TYPED_{na.namespace}_PATH_NORMALIZED", na, no
        if na.namespace == "DOS_DRIVE" and na.drive_or_volume != no.drive_or_volume:
            return False, "DOS_DRIVE_MISMATCH", na, no
        if na.namespace == "NT_DEVICE_VOLUME" and na.drive_or_volume != no.drive_or_volume:
            return False, "NT_VOLUME_MISMATCH", na, no
        return False, "DIRECTORY_OR_EXECUTABLE_MISMATCH", na, no

    # Explicitly refuse cross-namespace NT-device vs DOS-drive equivalence without same-event proof
    if {na.namespace, no.namespace} == {"NT_DEVICE_VOLUME", "DOS_DRIVE"}:
        return False, "UNVERIFIED_NT_DEVICE_MAPPING", na, no

    return False, "PATH_NAMESPACE_MISMATCH", na, no


def _path_family(field_name: str) -> str:
    f = str(field_name or "").strip().lower()
    if f in PARENT_PROCESS_PATH_FIELDS or "parent" in f:
        return "PARENT"
    if f in CHILD_PROCESS_PATH_FIELDS or "process" in f:
        return "CHILD"
    return "FILE"


def find_same_event_corroboration(
    *,
    claim_id: str,
    asserted_raw: Any,
    claim_field: str,
    cited_rec: CanonicalEvidenceRecord,
    all_records: List[CanonicalEvidenceRecord],
) -> Optional[Dict[str, Any]]:
    """Checks whether an NT-device path and DOS path share exact normalized full relative path on the SAME event."""
    if not cited_rec.source_event_id:
        return None
    ok, method, na, no = compare_paths_strict(
        asserted_raw,
        cited_rec.observed_value,
        claim_field=claim_field,
        obs_field=cited_rec.source_field,
    )
    if ok:
        return {
            "claim_id": claim_id,
            "source_event_id": cited_rec.source_event_id,
            "source_field": cited_rec.source_field,
            "original_value": str(cited_rec.observed_value),
            "normalized_value": no.normalized if no else "",
            "comparison_method": method,
            "alias_provenance": None,
            "validation_status": "GROUNDED",
            "validation_reason": "Direct typed path normalization matched cited telemetry.",
        }

    if method != "UNVERIFIED_NT_DEVICE_MAPPING" or not na or not no:
        return None

    # Require exact multi-segment relative path match (at least one directory separator, NEVER filename-only!)
    if "\\" not in no.relative_path or na.relative_path != no.relative_path:
        return None

    cited_family = _path_family(cited_rec.source_field)
    claim_family = _path_family(claim_field) if claim_field and claim_field != "unknown" else cited_family
    if cited_family != claim_family:
        return None

    for sib in all_records:
        if sib.incident_id != cited_rec.incident_id or sib.source_event_id != cited_rec.source_event_id:
            continue
        if sib.evidence_id == cited_rec.evidence_id or not is_path_field(sib.source_field):
            continue
        if _path_family(sib.source_field) != cited_family:
            continue

        sib_is_cmd = "command_line" in sib.source_field.lower() or "cmdline" in sib.source_field.lower()
        ns = normalize_executable_path(sib.observed_value, from_cmdline=sib_is_cmd)
        if not ns:
            continue

        # Sibling must directly prove the asserted namespace/drive & full relative path
        if ns.namespace == na.namespace and ns.normalized == na.normalized and ns.relative_path == no.relative_path:
            return {
                "claim_id": claim_id,
                "source_event_id": cited_rec.source_event_id,
                "source_field": cited_rec.source_field,
                "original_value": str(cited_rec.observed_value),
                "normalized_value": no.normalized,
                "comparison_method": "SAME_EVENT_CMDLINE_NT_VOLUME_CORROBORATED",
                "alias_provenance": sib.evidence_id,
                "validation_status": "GROUNDED",
                "validation_reason": (
                    f"Same-event corroboration: {sib.source_field} ({sib.evidence_id}) establishes DOS path "
                    f"'{ns.normalized}' with identical full relative path '{no.relative_path}' matching "
                    f"cited NT volume path '{no.normalized}'."
                ),
            }

    return None
