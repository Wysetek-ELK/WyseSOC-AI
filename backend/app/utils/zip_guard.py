import io
import os
import zipfile
from typing import List, Tuple, BinaryIO
from app.config import settings


class ZipSecurityException(Exception):
    pass


class ZipGuard:
    """
    Hardened ZIP archive inspection and validation to defend against:
    - Path traversal attacks (Zip Slip, e.g. ../../../etc/passwd)
    - Decompression bombs / zip bombs (unreasonable compression ratio or excessive uncompressed size)
    - File count floods (Denial of Service)
    - Corrupt or malformed zip headers
    """

    @classmethod
    def validate_and_extract_entries(
        cls, file_obj: BinaryIO
    ) -> List[Tuple[str, bytes]]:
        """
        Validates zip structure against security thresholds and extracts valid entries in memory.
        Returns a list of (sanitized_relative_path, content_bytes).
        """
        try:
            zf = zipfile.ZipFile(file_obj)
        except Exception as e:
            raise ZipSecurityException(f"Invalid or corrupted ZIP archive: {str(e)}")

        infolist = zf.infolist()

        if len(infolist) > settings.ZIP_MAX_FILE_COUNT:
            raise ZipSecurityException(
                f"ZIP contains {len(infolist)} files, which exceeds maximum allowed limit of {settings.ZIP_MAX_FILE_COUNT}"
            )

        total_uncompressed_size = 0
        total_compressed_size = 0
        extracted_entries: List[Tuple[str, bytes]] = []

        for info in infolist:
            # Skip directories
            if info.is_dir() or info.filename.endswith("/"):
                continue

            # Path Traversal Check (Zip Slip prevention)
            filename = info.filename.replace("\\", "/")
            if filename.startswith("/") or filename.startswith("../") or "/../" in filename or ":" in filename:
                raise ZipSecurityException(
                    f"Path traversal detected in archive entry: '{info.filename}'. Extraction aborted."
                )

            # Prevent normalized traversal
            normalized = os.path.normpath(filename).replace("\\", "/")
            if normalized.startswith("../") or normalized.startswith(".."):
                raise ZipSecurityException(
                    f"Normalized path traversal detected: '{info.filename}'. Extraction aborted."
                )

            # Per-file size check (e.g. max 25MB per file)
            max_single_file_size = 25 * 1024 * 1024
            if info.file_size > max_single_file_size:
                raise ZipSecurityException(
                    f"File '{info.filename}' size ({info.file_size} bytes) exceeds individual limit of {max_single_file_size} bytes"
                )

            total_uncompressed_size += info.file_size
            total_compressed_size += max(info.compress_size, 1)

            # Cumulative uncompressed size check (Bomb prevention)
            if total_uncompressed_size > settings.ZIP_MAX_UNCOMPRESSED_SIZE:
                raise ZipSecurityException(
                    f"Total uncompressed archive size exceeds limit of {settings.ZIP_MAX_UNCOMPRESSED_SIZE} bytes (possible zip bomb)"
                )

            # Ratio check
            ratio = total_uncompressed_size / total_compressed_size
            if ratio > settings.ZIP_MAX_RATIO and total_uncompressed_size > 5 * 1024 * 1024:
                raise ZipSecurityException(
                    f"Compression ratio ({ratio:.1f}:1) exceeds safety threshold of {settings.ZIP_MAX_RATIO}:1 (zip bomb detected)"
                )

            try:
                content = zf.read(info)
                extracted_entries.append((normalized, content))
            except Exception as e:
                raise ZipSecurityException(f"Error decompressing '{info.filename}': {str(e)}")

        return extracted_entries

