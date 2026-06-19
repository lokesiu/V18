"""
zip_builder.py - ZIP Package Builder for 明证台 V18

Creates client delivery ZIP packages from generated documents.
"""
from __future__ import annotations

import os
import zipfile
import logging

logger = logging.getLogger(__name__)

# File extensions to include in the delivery package
_DELIVERY_EXTENSIONS = (".docx", ".pdf", ".xlsx")


def build_zip(source_dir: str, output_path: str) -> bool:
    """Create a ZIP package from source_dir contents.

    Includes all .docx, .pdf, and .xlsx files found in source_dir
    (non-recursive, top-level only).

    Args:
        source_dir: Directory containing files to package.
        output_path: Path for the output ZIP file.

    Returns:
        True on success, False on failure.
    """
    try:
        if not os.path.isdir(source_dir):
            logger.error("Source directory does not exist: %s", source_dir)
            return False

        # Collect delivery files
        files_to_include: list[str] = []
        for entry in sorted(os.listdir(source_dir)):
            full_path = os.path.join(source_dir, entry)
            if os.path.isfile(full_path) and entry.lower().endswith(_DELIVERY_EXTENSIONS):
                files_to_include.append(full_path)

        if not files_to_include:
            logger.warning("No delivery files found in %s", source_dir)
            # Create empty ZIP rather than fail
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("README.txt", "本交付包中暂无生成文件。\n请先运行完整的分析流程。")
            logger.info("Empty delivery ZIP created: %s", output_path)
            return True

        # Create ZIP
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in files_to_include:
                arcname = os.path.basename(file_path)
                zf.write(file_path, arcname)
                logger.debug("Added to ZIP: %s", arcname)

        file_count = len(files_to_include)
        zip_size = os.path.getsize(output_path)
        logger.info(
            "Delivery ZIP created: %s (%d files, %d bytes)",
            output_path,
            file_count,
            zip_size,
        )
        return True

    except Exception as exc:
        logger.error("Failed to build ZIP package: %s", exc)
        return False
