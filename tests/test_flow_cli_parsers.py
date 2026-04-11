from __future__ import annotations

import unittest

from media_tools.transcribe.cli.run_api import build_parser as build_run_parser
from media_tools.transcribe.cli.run_batch import build_parser as build_batch_parser


class FlowCliParserTests(unittest.TestCase):
    def test_run_parser_accepts_output_dir_and_export_concurrency(self) -> None:
        args = build_run_parser().parse_args(
            ["sample.mp4", "--output-dir", "exports", "--export-concurrency", "4"]
        )

        self.assertEqual(args.output_dir, "exports")
        self.assertEqual(args.export_concurrency, 4)

    def test_batch_parser_accepts_download_dir_alias(self) -> None:
        args = build_batch_parser().parse_args(["first.mp4", "--download-dir", "exports"])

        self.assertEqual(args.output_dir, "exports")

    def test_batch_parser_accepts_directory_grouping_options(self) -> None:
        args = build_batch_parser().parse_args(
            ["media", "--pattern", "*.mp4", "--recursive", "--group-size", "10"]
        )

        self.assertEqual(args.pattern, "*.mp4")
        self.assertTrue(args.recursive)
        self.assertEqual(args.group_size, 10)

    def test_run_parser_uses_command_specific_prog(self) -> None:
        self.assertEqual(build_run_parser().prog, "qwen-transcribe run")
