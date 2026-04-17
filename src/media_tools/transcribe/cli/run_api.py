from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qwen-transcribe run")
    parser.add_argument("source", help="Local media file path")
    parser.add_argument("--output-dir", dest="output_dir", default="", help="Output directory")
    parser.add_argument(
        "--export-concurrency",
        dest="export_concurrency",
        type=int,
        default=2,
        help="Max concurrent export tasks",
    )
    return parser
