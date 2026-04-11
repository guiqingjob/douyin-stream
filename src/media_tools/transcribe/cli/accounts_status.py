from __future__ import annotations

import asyncio

from ..account_status import collect_account_statuses
from ..runtime import enable_live_output, load_dotenv


def fmt(value: object) -> str:
    return "-" if value in {None, ""} else str(value)


def pad(value: object, width: int) -> str:
    return str(value).ljust(width)


async def run(argv: list[str] | None = None) -> int:
    del argv
    load_dotenv()
    enable_live_output()
    statuses = await collect_account_statuses()
    rows = [
        {
            "account": status["accountId"],
            "label": status["accountLabel"],
            "auth": "yes" if status["authExists"] else "no",
            "quota": (
                f"{status['quota'].remaining_upload}/{status['quota'].total_upload}"
                if status["quota"] is not None
                else "-"
            ),
            "consumed": status["daily"]["consumedMinutes"],
            "claimedToday": "yes" if status["daily"]["lastEquityClaimAt"] else "no",
            "lastClaimAt": status["daily"]["lastEquityClaimAt"] or "",
            "action": status["action"],
            "note": status["note"],
        }
        for status in statuses
    ]

    widths = {
        "account": max(max((len(row["account"]) for row in rows), default=0), 7),
        "label": max(max((len(row["label"]) for row in rows), default=0), 5),
        "auth": 4,
        "quota": max(max((len(row["quota"]) for row in rows), default=0), 5),
        "consumed": max(max((len(str(row["consumed"])) for row in rows), default=0), 8),
        "claimedToday": 7,
        "action": max(max((len(row["action"]) for row in rows), default=0), 6),
    }

    print("")
    print(
        "  ".join(
            [
                pad("account", widths["account"]),
                pad("label", widths["label"]),
                pad("auth", widths["auth"]),
                pad("quota", widths["quota"]),
                pad("consumed", widths["consumed"]),
                pad("claimed", widths["claimedToday"]),
                pad("action", widths["action"]),
                "note",
            ]
        )
    )

    for row in rows:
        print(
            "  ".join(
                [
                    pad(row["account"], widths["account"]),
                    pad(row["label"], widths["label"]),
                    pad(row["auth"], widths["auth"]),
                    pad(row["quota"], widths["quota"]),
                    pad(fmt(row["consumed"]), widths["consumed"]),
                    pad(row["claimedToday"], widths["claimedToday"]),
                    pad(row["action"], widths["action"]),
                    row["note"],
                ]
            )
        )
        if row["lastClaimAt"]:
            print(f"  last claim at: {row['lastClaimAt']}")

    print("")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
