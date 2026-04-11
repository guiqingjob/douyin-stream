from __future__ import annotations

import asyncio

from ..account_status import collect_account_statuses
from ..accounts import resolve_auth_state_path
from ..quota import claim_equity_quota
from ..runtime import enable_live_output, load_dotenv
from .common import ensure_auth_state_exists


async def run(argv: list[str] | None = None) -> int:
    del argv
    load_dotenv()
    enable_live_output()
    statuses = await collect_account_statuses()
    targets = [status for status in statuses if status["action"] == "claim-today"]

    print("")
    if not targets:
        print("no accounts currently need an equity claim")
        print("")
        return 0

    for status in targets:
        account_id = "" if status["accountId"] == "default" else status["accountId"]
        account = resolve_auth_state_path(account_id=account_id)
        ensure_auth_state_exists(account)
        label = f"{account.account_label} ({account.account_id})" if account.account_id else "default"
        print(f"claiming equity for: {label}")
        result = await claim_equity_quota(
            account_id=account.account_id,
            auth_state_path=account.auth_state_path,
            force=False,
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

    print("")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
