from __future__ import annotations

import argparse
import asyncio

from ..accounts import load_accounts_config, resolve_auth_state_path
from ..config import load_config
from ..quota import claim_equity_quota
from ..runtime import enable_live_output, load_dotenv
from .common import command_parser, ensure_auth_state_exists


def build_parser() -> argparse.ArgumentParser:
    parser = command_parser("quota claim", "Refresh Qwen equity quota for one or more accounts.")
    parser.add_argument("--account", default=load_config().default_account, help="Use a specific account id")
    parser.add_argument("--all", action="store_true", help="Run against every configured account")
    parser.add_argument("--force", action="store_true", help="Claim even if today is already marked as claimed")
    return parser


def resolve_target_accounts(account_id: str, use_all: bool):
    if account_id:
        return [resolve_auth_state_path(account_id=account_id)]

    _, accounts = load_accounts_config()
    if use_all and accounts:
        return [resolve_auth_state_path(account_id=account.id) for account in accounts]
    if accounts:
        return [resolve_auth_state_path(account_id=accounts[0].id)]
    return [resolve_auth_state_path(account_id="")]


async def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    enable_live_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    for account in resolve_target_accounts(args.account, args.all):
        ensure_auth_state_exists(account)
        label = f"{account.account_label} ({account.account_id})" if account.account_id else "default"
        print(f"claiming equity for: {label}")
        result = await claim_equity_quota(
            account_id=account.account_id,
            auth_state_path=account.auth_state_path,
            force=args.force,
        )
        if result.skipped:
            print(f"skipped: {result.reason}")
            continue
        if result.before_snapshot is None or result.after_snapshot is None:
            print(f"error: quota snapshot missing for {label}")
            continue
        print(
            "before remaining upload: "
            f"{result.before_snapshot.remaining_upload}/{result.before_snapshot.total_upload}"
        )
        print(
            "after remaining upload: "
            f"{result.after_snapshot.remaining_upload}/{result.after_snapshot.total_upload}"
        )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
