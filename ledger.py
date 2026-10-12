"""Append-only, in-memory multi-currency ledger replay for the six-day exercise."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

D = Decimal
DAYS = range(1, 7)
FEE_AED = D("25.00")
DAILY_RATE = D("0.0004")  # 0.04% per day

CURRENCIES = {"ACC-001": ("AED", 2), "ACC-002": ("BHD", 3)}
OPENING = {"ACC-001": D("0.00"), "ACC-002": D("0.000")}


def quantum(account: str) -> Decimal:
    return D(1).scaleb(-CURRENCIES[account][1])


def money(account: str, amount: Decimal) -> Decimal:
    return amount.quantize(quantum(account), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Event:
    event_id: str
    posted_day: int
    kind: str
    account: str
    amount: Decimal = D("0")
    value_day: int = 0
    auth_id: str = ""
    target_event: str = ""
    installments: int = 0


@dataclass(frozen=True)
class Entry:
    entry_id: str
    account: str
    amount: Decimal  # signed ledger movement
    value_day: int
    source: str
    description: str


@dataclass
class Authorization:
    auth_id: str
    account: str
    amount: Decimal
    approved: bool
    active_hold: Decimal
    state: str


class Ledger:
    def __init__(self) -> None:
        self.entries: list[Entry] = []
        self.auths: dict[str, Authorization] = {}
        self.errors: list[str] = []
        self.event_status: dict[str, str] = {}
        self.assessed_fee_days: set[tuple[str, int]] = set()
        self.fee_log: list[tuple[str, int, Decimal]] = []
        self.events: dict[str, Event] = {}
        self.daily_interest: dict[str, dict[int, Decimal]] = {}
        self.capitalized: dict[str, Decimal] = {}

    def base_balance(self, account: str, day: int) -> Decimal:
        return money(account, OPENING[account] + sum(
            (e.amount for e in self.entries if e.account == account and e.value_day <= day), D("0")
        ))

    def active_holds(self, account: str) -> Decimal:
        return sum((a.active_hold for a in self.auths.values()
                    if a.account == account and a.approved), D("0"))

    def available_balance(self, account: str, day: int) -> Decimal:
        return money(account, self.base_balance(account, day) - self.active_holds(account))

    def add_entry(self, entry: Entry) -> None:
        # Append-only: existing entries are never edited or removed.
        self.entries.append(entry)

    def assess_new_fees(self, through_day: int) -> None:
        """Assess each newly discovered negative account/day once; backdated entries
        can cause a fee to be discovered for an earlier value date.
        """
        for account, (currency, _) in CURRENCIES.items():
            if currency != "AED":
                continue  # exercise defines the overdraft fee as AED; no BHD conversion rule supplied
            for day in range(1, through_day + 1):
                key = (account, day)
                if key in self.assessed_fee_days:
                    continue
                if self.base_balance(account, day) < 0:
                    fee = money(account, -FEE_AED)
                    self.add_entry(Entry(f"FEE-{account}-D{day}", account, fee, day,
                                         "SYSTEM", f"Overdraft fee assessed for Day {day}"))
                    self.assessed_fee_days.add(key)
                    self.fee_log.append((account, day, fee))

    def process(self, event: Event) -> None:
        self.events[event.event_id] = event
        account = event.account
        amount = money(account, event.amount)
        if event.kind in {"CREDIT", "DEBIT"}:
            signed = amount if event.kind == "CREDIT" else -amount
            self.add_entry(Entry(event.event_id, account, signed, event.value_day,
                                 event.event_id, event.kind))
            self.event_status[event.event_id] = "POSTED"
        elif event.kind == "AUTHORIZATION":
            if amount <= 0:
                self.errors.append(f"{event.event_id}: authorization amount must be positive")
                self.event_status[event.event_id] = "REJECTED"
            else:
                available_after_hold = money(account, self.base_balance(account, event.value_day)
                                             - self.active_holds(account) - amount)
                approved = available_after_hold >= 0
                state = "APPROVED_ACTIVE" if approved else "DECLINED_INSUFFICIENT_FUNDS"
                self.auths[event.auth_id] = Authorization(event.auth_id, account, amount,
                                                          approved, amount if approved else D("0"), state)
                self.event_status[event.event_id] = state
                if not approved:
                    self.errors.append(f"{event.event_id}: {event.auth_id} declined; available after hold would be {available_after_hold}")
        elif event.kind == "SETTLEMENT":
            auth = self.auths.get(event.auth_id)
            if auth is None or not auth.approved or auth.active_hold <= 0:
                self.errors.append(f"{event.event_id}: rejected settlement; no active approved authorization {event.auth_id}")
                self.event_status[event.event_id] = "REJECTED_UNKNOWN_OR_INACTIVE_AUTH"
            elif amount <= 0 or amount > auth.amount:
                self.errors.append(f"{event.event_id}: rejected settlement amount {amount}; authorization ceiling is {auth.amount}")
                self.event_status[event.event_id] = "REJECTED_INVALID_AMOUNT"
            else:
                # Settle actual amount and release the full authorization hold.
                self.add_entry(Entry(event.event_id, account, -amount, event.value_day,
                                     event.event_id, f"Settlement {event.auth_id}"))
                auth.active_hold = D("0")
                auth.state = f"SETTLED_{amount}"
                self.event_status[event.event_id] = "ACCEPTED"
        elif event.kind == "REVERSAL":
            target = self.events.get(event.target_event)
            target_entry = next((e for e in self.entries if e.entry_id == event.target_event), None)
            if target is None or target_entry is None:
                self.errors.append(f"{event.event_id}: rejected reversal; target {event.target_event} is not a posted ledger entry")
                self.event_status[event.event_id] = "REJECTED_UNKNOWN_TARGET"
            else:
                # Compensating entry uses the target's original value date. Original entry remains intact.
                self.add_entry(Entry(event.event_id, target_entry.account, -target_entry.amount,
                                     target_entry.value_day, event.event_id,
                                     f"Reversal of {event.target_event}; requested value day {event.value_day}"))
                self.event_status[event.event_id] = "POSTED_COMPENSATING_ENTRY"
        elif event.kind == "INSTALMENT_CREDIT":
            n = event.installments
            if n < 1:
                self.errors.append(f"{event.event_id}: instalment count must be positive")
                self.event_status[event.event_id] = "REJECTED"
            else:
                total = amount
                q = quantum(account)
                base = (total / D(n)).quantize(q, rounding=ROUND_HALF_UP)
                pieces = [base for _ in range(n - 1)]
                pieces.append(money(account, total - sum(pieces, D("0"))))
                for idx, piece in enumerate(pieces, 1):
                    self.add_entry(Entry(f"{event.event_id}-I{idx}", account, piece,
                                         event.value_day, event.event_id,
                                         f"Instalment {idx}/{n}"))
                self.event_status[event.event_id] = "POSTED_INSTALMENTS " + ", ".join(map(str, pieces))
        else:
            self.errors.append(f"{event.event_id}: unsupported event kind {event.kind}")
            self.event_status[event.event_id] = "REJECTED_UNSUPPORTED"

        # A late-posted, backdated debit can reveal historical overdrafts.
        self.assess_new_fees(event.posted_day)

    def capitalize_interest(self) -> None:
        """Calculate rounded daily accruals on final replayed closing balances,
        then post one capitalized credit with value date Day 6.
        """
        for account in CURRENCIES:
            daily: dict[int, Decimal] = {}
            for day in DAYS:
                close = self.base_balance(account, day)
                accrual = money(account, max(close, D("0")) * DAILY_RATE)
                daily[day] = accrual
            total = money(account, sum(daily.values(), D("0")))
            self.daily_interest[account] = daily
            self.capitalized[account] = total
            if total:
                self.add_entry(Entry(f"INTEREST-{account}-D6", account, total, 6,
                                     "SYSTEM", "Six-day interest capitalized"))

    def report(self) -> str:
        lines = ["IN-MEMORY LEDGER REPLAY — six days", "Amounts are signed ledger movements; holds are not ledger entries."]
        for day in DAYS:
            lines.append(f"\nDay {day}")
            for account, (currency, places) in CURRENCIES.items():
                close = self.base_balance(account, day)
                holds = self.active_holds(account)
                available = money(account, close - holds)
                fee_today = [f"{amt:.{places}f} {currency}" for acc, d, amt in self.fee_log if acc == account and d == day]
                fee_text = ", ".join(fee_today) if fee_today else "none"
                lines.append(f"  {account}: closing={close:.{places}f} {currency}; active_holds_now={holds:.{places}f}; available_now={available:.{places}f}; fee_assessed={fee_text}")
                if account in self.daily_interest:
                    lines.append(f"    interest_accrual={self.daily_interest[account][day]:.{places}f} {currency}")
            if day == 2:
                lines.append(f"  Authorization Auth-A at E3: {self.event_status.get('E3', 'not processed')} (later settled on Day 4)")
            if day == 4:
                lines.append(f"  Settlement E5/Auth-A: {self.event_status.get('E5', 'not processed')}")
                lines.append(f"  Settlement E6/Auth-Z: {self.event_status.get('E6', 'not processed')}")
            if day == 5:
                lines.append(f"  Authorization Auth-B: {self.auths.get('Auth-B').state if 'Auth-B' in self.auths else 'not processed'}")
        lines.append("\nCapitalized interest at end of Day 6:")
        for account, total in self.capitalized.items():
            currency, places = CURRENCIES[account]
            lines.append(f"  {account}: {total:.{places}f} {currency} (sum of rounded daily accruals)")
        lines.append("\nErrors:")
        lines.extend(f"  - {e}" for e in self.errors) if self.errors else lines.append("  none")
        lines.append("\nEvent statuses:")
        lines.extend(f"  {eid}: {status}" for eid, status in self.event_status.items())
        return "\n".join(lines)


def event_stream() -> list[Event]:
    return [
        Event("E1", 1, "CREDIT", "ACC-001", D("1200.00"), 1),
        Event("E2", 1, "DEBIT", "ACC-001", D("950.00"), 1),
        Event("E3", 2, "AUTHORIZATION", "ACC-001", D("200.00"), 2, auth_id="Auth-A"),
        Event("E4", 3, "CREDIT", "ACC-001", D("400.00"), 3),
        Event("E5", 4, "SETTLEMENT", "ACC-001", D("185.00"), 4, auth_id="Auth-A"),
        Event("E6", 4, "SETTLEMENT", "ACC-001", D("180.00"), 4, auth_id="Auth-Z"),
        Event("E7", 5, "DEBIT", "ACC-001", D("620.00"), 2),
        Event("E8", 5, "AUTHORIZATION", "ACC-001", D("90.00"), 5, auth_id="Auth-B"),
        Event("E9", 6, "REVERSAL", "ACC-001", D("620.00"), 2, target_event="E7"),
        Event("E10", 5, "INSTALMENT_CREDIT", "ACC-002", D("10.000"), 5, installments=3),
    ]


def run() -> Ledger:
    ledger = Ledger()
    # Preserve the supplied stream order exactly; E10 is after E9 in this list only
    # if the input says so. The stated prompt order puts E10 after E9, posted on Day 5.
    for event in event_stream():
        ledger.process(event)
    ledger.capitalize_interest()
    print(ledger.report())
    return ledger


if __name__ == "__main__":
    run()
