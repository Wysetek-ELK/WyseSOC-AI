import io
import zipfile
import pytest
from app.utils.zip_guard import ZipGuard, ZipSecurityException


def test_valid_zip_extraction():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test_folder/incident_1.json", '{"incidentId": "123"}')
        zf.writestr("Rule_info.txt", "Name\nTest Rule\nEvent Type\nTEST_RULE")
    buf.seek(0)

    entries = ZipGuard.validate_and_extract_entries(buf)
    assert len(entries) == 2
    filenames = [e[0] for e in entries]
    assert "test_folder/incident_1.json" in filenames
    assert "Rule_info.txt" in filenames


def test_path_traversal_zip_slip_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil_file.txt", "malicious payload")
    buf.seek(0)

    with pytest.raises(ZipSecurityException) as exc_info:
        ZipGuard.validate_and_extract_entries(buf)
    assert "Path traversal detected" in str(exc_info.value) or "Normalized path traversal" in str(exc_info.value)


def test_normalized_path_traversal_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("subfolder/../../etc/passwd", "root:x:0:0:")
    buf.seek(0)

    with pytest.raises(ZipSecurityException) as exc_info:
        ZipGuard.validate_and_extract_entries(buf)
    assert "Path traversal detected" in str(exc_info.value) or "Normalized path traversal" in str(exc_info.value)


def test_corrupted_zip_handled():
    buf = io.BytesIO(b"not a valid zip file binary garbage")
    with pytest.raises(ZipSecurityException) as exc_info:
        ZipGuard.validate_and_extract_entries(buf)
    assert "Invalid or corrupted ZIP" in str(exc_info.value)

