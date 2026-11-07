import unittest

import numpy as np
import pandas as pd

from ashare_lab.backtest import metrics, run_backtest


class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.calendar = pd.bdate_range("2020-01-30", "2020-03-03")
        self.prices = pd.DataFrame([
            dict(date=day, symbol=symbol, adj_open=10.0, adj_close=10.0,
                 can_buy=True, can_sell=True, status_known=True)
            for day in self.calendar for symbol in ["A", "B"]
        ])
        self.factors = pd.DataFrame([
            dict(date=pd.Timestamp(day), symbol=symbol, composite=score)
            for day in ["2020-01-31", "2020-02-28"]
            for symbol, score in ([('A', 1), ('B', 0)] if day == "2020-01-31" else [('A', 0), ('B', 1)])
        ])
        self.config = dict(start="2020-01-30", end="2020-03-03", top_n=1, initial_cash=1000,
                           commission_bps=0, slippage_bps=0, sell_tax_bps=0, allow_unknown_status=False)

    def change(self, symbol, day, **values):
        mask = (self.prices.symbol == symbol) & (self.prices.date == pd.Timestamp(day))
        for column, value in values.items():
            self.prices.loc[mask, column] = value

    def run_engine(self, **overrides):
        return run_backtest(self.prices, self.factors, self.calendar, self.config | overrides)

    def test_close_signal_executes_next_open_without_prior_overnight_gain(self):
        self.change("A", "2020-02-03", adj_open=20, adj_close=22)
        result = self.run_engine()
        first = result.trades.iloc[0]
        self.assertEqual(first.date, pd.Timestamp("2020-02-03"))
        self.assertEqual(first.signal_date, pd.Timestamp("2020-01-31"))
        self.assertAlmostEqual(first.quantity, 50)
        self.assertAlmostEqual(result.daily.set_index("date").loc["2020-02-03", "nav"], 1.1)
        self.assertTrue((result.daily.loc[result.daily.date <= "2020-01-31", "nav"] == 1).all())

    def test_existing_holding_gets_overnight_before_sale(self):
        self.change("A", "2020-03-02", adj_open=20, adj_close=20)
        result = self.run_engine()
        day = result.daily.set_index("date").loc["2020-03-02"]
        self.assertAlmostEqual(day["nav"], 2)
        self.assertAlmostEqual(result.trades.query("side == 'buy' and symbol == 'B'").iloc[0].quantity, 200)

    def test_blocked_buy_leaves_cash_and_expires(self):
        self.change("A", "2020-02-03", can_buy=False)
        result = self.run_engine()
        self.assertEqual(result.orders.iloc[0].reason, "buy_blocked")
        self.assertFalse(((result.trades.symbol == "A") & (result.trades.side == "buy")).any())
        self.assertAlmostEqual(result.daily.set_index("date").loc["2020-02-04", "cash"], 1000)

    def test_blocked_sale_keeps_position_and_does_not_borrow(self):
        self.change("A", "2020-03-02", can_sell=False)
        result = self.run_engine()
        self.assertIn("sell_blocked", result.orders.reason.tolist())
        self.assertIn("insufficient_cash", result.orders.reason.tolist())
        last = result.positions.loc[result.positions.date == self.calendar[-1]]
        self.assertEqual(last.symbol.tolist(), ["A"])
        self.assertTrue((result.daily.cash >= 0).all())

    def test_costs_paid_at_first_fill_and_wealth_matches_cash(self):
        result = self.run_engine(commission_bps=10, slippage_bps=20, sell_tax_bps=5)
        buy = result.trades.iloc[0]
        expected_quantity = 1000 / (10 * 1.002 * 1.001)
        self.assertAlmostEqual(buy.quantity, expected_quantity)
        day = result.daily.set_index("date").loc["2020-02-03"]
        self.assertAlmostEqual(day["equity"], expected_quantity * 10)
        self.assertAlmostEqual(day["cost"], 1000 - expected_quantity * 10)
        self.assertTrue((result.daily.cash >= 0).all())
        self.assertLess(result.daily.nav.iloc[-1], self.run_engine().daily.nav.iloc[-1])

    def test_partial_buy_scales_names_proportionally(self):
        result = run_backtest(self.prices, self.factors, self.calendar,
                              self.config | dict(commission_bps=100), score_column=None)
        buys = result.trades.query("side == 'buy'")
        self.assertAlmostEqual(buys.iloc[0].quantity, buys.iloc[1].quantity)
        self.assertTrue((result.daily.cash >= 0).all())

    def test_missing_held_row_fails_instead_of_forward_fill(self):
        mask = (self.prices.symbol == "A") & (self.prices.date == pd.Timestamp("2020-02-04"))
        self.prices = self.prices.loc[~mask]
        with self.assertRaisesRegex(ValueError, "Missing held price"):
            self.run_engine()

    def test_unknown_flags_require_explicit_assumption(self):
        self.change("A", "2020-02-03", status_known=False)
        with self.assertRaisesRegex(ValueError, "Unknown execution status"):
            self.run_engine()
        self.assertGreater(len(self.run_engine(allow_unknown_status=True).trades), 0)

    def test_ranking_ties_are_stable(self):
        self.factors["composite"] = 0
        first = self.run_engine().trades.iloc[0]
        self.assertEqual(first.symbol, "A")

    def test_no_future_factor_rewrite_changes_earlier_holdings(self):
        first = self.run_engine()
        self.factors.loc[self.factors.date == pd.Timestamp("2020-02-28"), "composite"] *= -1
        second = self.run_engine()
        pd.testing.assert_frame_equal(first.daily.loc[first.daily.date < "2020-03-02"],
                                      second.daily.loc[second.daily.date < "2020-03-02"])

    def test_metrics_keep_initial_loss_and_initial_drawdown(self):
        daily = pd.DataFrame({"return": [-.1, 0], "turnover": [1, 0], "cost": [100, 0]})
        m = metrics(daily)
        self.assertAlmostEqual(m["total_return"], -.1)
        self.assertAlmostEqual(m["max_drawdown"], -.1)
        self.assertAlmostEqual(m["total_cost"], 100)
        self.assertAlmostEqual(m["annual_turnover"], 126)


if __name__ == "__main__":
    unittest.main()
