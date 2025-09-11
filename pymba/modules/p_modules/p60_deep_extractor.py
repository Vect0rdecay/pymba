#!/usr/bin/env python3
"""
P60 - Deep Extractor

This module performs deep extraction for nested archives and
complex firmware structures that may require multiple extraction passes.
"""

import os
import sys
from pathlib import Path
import subprocess
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P60_deep_extractor(BasePModule):
    """P60 - Deep extractor module."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P60_deep_extractor"
        self.pre_thread_ena = 0  # Disable threading for extraction
        self.max_depth = getattr(config, 'deep_extract_max_depth', 2)
        self.extraction_root = os.path.join(config.log_dir, "firmware", "deep_extracted")
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Deep firmware extractor")
        self.pre_module_reporter()
        try:
            if os.path.isdir(self.firmware_path):
                # Start deep scan on directory content
                input_paths = [self.firmware_path]
            elif os.path.isfile(self.firmware_path):
                input_paths = [self.firmware_path]
            else:
                self.print_output("No valid firmware input for deep extraction")
                self.module_end_log()
                return 0

            Path(self.extraction_root).mkdir(parents=True, exist_ok=True)
            extracted_any = self._deep_extract(input_paths, self.extraction_root, depth=0)
            if extracted_any:
                root_dir = self.detect_root_directory(self.extraction_root)
                if root_dir:
                    self.root_directories.append(root_dir)
                    self.extraction_success = True
                    self.print_success(f"Deep extraction found root directory: {root_dir}")
            else:
                self.print_output("Deep extraction found no nested archives")
            return 0
        except Exception as e:
            self.print_error(f"Error in deep extraction: {e}")
            return 1
        finally:
            self.module_end_log()

    def _deep_extract(self, inputs, out_dir, depth):
        if depth > self.max_depth:
            return False
        found_any = False
        for path in inputs:
            path_obj = Path(path)
            if path_obj.is_dir():
                # Recurse into directory
                child_paths = [str(p) for p in path_obj.iterdir()]
                if self._deep_extract(child_paths, out_dir, depth + 1):
                    found_any = True
                continue
            # Try extracting with patool (via patoolib CLI if available)
            if self._looks_like_archive(path_obj):
                target_dir = Path(out_dir) / f"depth{depth}_{path_obj.stem}"
                target_dir.mkdir(parents=True, exist_ok=True)
                ok = self._try_extract_with_patool(str(path_obj), str(target_dir))
                if ok:
                    found_any = True
                    # Recurse into extracted content
                    child_paths = [str(p) for p in target_dir.iterdir()]
                    if self._deep_extract(child_paths, out_dir, depth + 1):
                        found_any = True
        return found_any

    def _looks_like_archive(self, path: Path) -> bool:
        archive_exts = {
            '.bin', '.img', '.iso', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.lzma',
            '.zip', '.7z', '.rar', '.cpio', '.squashfs'
        }
        if path.suffix.lower() in archive_exts:
            return True
        try:
            with open(path, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'PK') or header.startswith(b'\x1f\x8b'):
                    return True
        except Exception:
            pass
        return False

    def _try_extract_with_patool(self, src: str, dst: str) -> bool:
        # Prefer patool CLI if available
        try:
            result = subprocess.run(['patool', 'extract', '--outdir', dst, src],
                                    capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                self.print_output(f"Extracted {os.path.basename(src)} -> {dst}")
                return True
            else:
                self.print_output(f"patool failed ({result.returncode}), trying python patoolib if available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # Fallback to python patoolib API
        try:
            import patoolib
            patoolib.extract_archive(src, outdir=dst, verbosity=-1)
            self.print_output(f"Extracted (python) {os.path.basename(src)} -> {dst}")
            return True
        except Exception as e:
            self.print_output(f"patool extraction failed for {src}: {e}")
            return False
