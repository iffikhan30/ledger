import unittest
from decimal import Decimal as D
from ledger import Ledger, event_stream


class LedgerTests(unittest.TestCase):
    def build(self):
        ledger = Ledger()
        for event in event_stream():
            ledger.process(event)
        ledger.capitalize_interest()
        return ledger

    def test_authorization_and_settlement_states(self):
        ledger = self.build()
        self.assertEqual(ledger.event_status['E3'], 'APPROVED_ACTIVE')
        self.assertEqual(ledger.event_status['E5'], 'ACCEPTED')
        self.assertEqual(ledger.event_status['E6'], 'REJECTED_UNKNOWN_OR_INACTIVE_AUTH')
        self.assertEqual(ledger.event_status['E8'], 'DECLINED_INSUFFICIENT_FUNDS')

    def test_late_debit_changes_historical_closing_balance(self):
        ledger = self.build()
        # Day 2 before fee assessment was -370.00. The assessed fee is itself
        # an append-only Day 2 entry, and E9 later compensates for E7.
        self.assertEqual(ledger.base_balance('ACC-001', 2), D('225.00'))
        self.assertEqual(ledger.base_balance('ACC-001', 1), D('250.00'))

    def test_fee_assessments_are_once_per_account_day_and_not_deleted(self):
        ledger = self.build()
        self.assertEqual(ledger.fee_log, [
            ('ACC-001', 2, D('-25.00')),
            ('ACC-001', 4, D('-25.00')),
            ('ACC-001', 5, D('-25.00')),
        ])
        self.assertEqual(len([e for e in ledger.entries if e.entry_id == 'E7']), 1)
        self.assertEqual(len([e for e in ledger.entries if e.entry_id == 'E9']), 1)

    def test_bhd_instalments_sum_exactly_to_total(self):
        ledger = self.build()
        pieces = [e.amount for e in ledger.entries if e.source == 'E10']
        self.assertEqual(pieces, [D('3.333'), D('3.333'), D('3.334')])
        self.assertEqual(sum(pieces, D('0')), D('10.000'))

    def test_interest_daily_rounding_sums_to_capitalized_amount(self):
        ledger = self.build()
        for account in ('ACC-001', 'ACC-002'):
            self.assertEqual(sum(ledger.daily_interest[account].values(), D('0')),
                             ledger.capitalized[account])

    def test_holds_do_not_change_ledger_balance(self):
        ledger = Ledger()
        for event in event_stream()[:3]:
            ledger.process(event)
        self.assertEqual(ledger.base_balance('ACC-001', 2), D('250.00'))
        self.assertEqual(ledger.active_holds('ACC-001'), D('200.00'))
        self.assertEqual(ledger.available_balance('ACC-001', 2), D('50.00'))


if __name__ == '__main__':
    unittest.main()
