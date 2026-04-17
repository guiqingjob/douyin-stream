from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qwen-transcribe batch")
    parser.add_argument("sources", nargs="+", help="Local media file or directory")
    parser.add_argument("--output-dir", dest="output_dir", default="", help="Output directory")
    parser.add_argument("--download-dir", dest="output_dir", help="Alias for --output-dir")
    parser.add_argument("--pattern", dest="pattern", default="*.mp4", help="File pattern to include")
    parser.add_argument("--recursive", dest="recursive", action="store_true", help="Scan directories recursively")
    parser.add_argument("--group-size", dest="group_size", type=int, default=1, help="Paths per batch group")
    return parser
