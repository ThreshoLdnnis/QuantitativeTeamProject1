"""Numerical, calendar alignment and temporal isolation checks."""

import unittest

import numpy as np
import pandas as pd

from ashare_lab.factors import compute_factors, monthly_signal_dates
from ashare_lab.research import analyze_factors, build_forward_labels


def sample_prices(days, n=6):
    rows = []
    for j in range(n):
        for i, day in enumerate(days):
            close = 10.0 * (1.0 + 0.001 * (j + 1)) ** i
            rows.append({"date": day, "symbol": f"S{j:03d}", "adj_close": close,
                         "adj_open": close * (1.0 + i * 0.0001),
                         "volume": 100.0 + i * (j + 1), "turnover": 0.01 + 0.001 * j})
    return pd.DataFrame(rows)


def members(prices):
    return prices[["date", "symbol"]].assign(eligible=True)


def settings(**kwargs):
    cfg = {"lookback": 20, "activity_short": 5, "activity_long": 20,
           "activity_mode": "relative_volume", "groups": 5,
           "directions": {"momentum": 1, "volatility": -1, "activity": -1},
           "mad_scale": 3.0, "start": "2020-01-01", "end": "2021-12-31",
           "splits": {"development": ["2020-01-01", "2020-12-31"],
                      "test": ["2021-01-01", "2021-12-31"]}}
    cfg.update(kwargs)
    return cfg


class FactorTests(unittest.TestCase):
    def test_known_formulas_and_signed_normalization(self):
        days = pd.bdate_range("2020-01-01", periods=30)
        prices = sample_prices(days)
        # A variable return path tests sample std, not only a constant-return path.
        for j in range(6):
            selection = prices["symbol"].eq(f"S{j:03d}")
            prices.loc[selection, "adj_close"] = 10 * np.cumprod(1 + np.arange(30) * 0.0005 * (j + 1))
        idx = prices["symbol"].eq("S000")
        factors = compute_factors(prices, members(prices), settings())
        row = factors.loc[(factors["date"] == days[25]) & factors["symbol"].eq("S000")].iloc[0]
        stock = prices.loc[idx].reset_index(drop=True)
        self.assertAlmostEqual(row["momentum"], stock.loc[25, "adj_close"] / stock.loc[5, "adj_close"] - 1)
        self.assertAlmostEqual(row["volatility"], stock["adj_close"].pct_change().iloc[6:26].std(ddof=1))
        self.assertAlmostEqual(row["activity"], stock["volume"].iloc[21:26].mean() / stock["volume"].iloc[6:26].mean())
        cross = factors.loc[factors["date"].eq(days[25])]
        for column in ["z_momentum", "z_volatility", "z_activity"]:
            self.assertAlmostEqual(cross[column].mean(), 0.0, places=12)
            self.assertAlmostEqual(cross[column].std(ddof=0), 1.0, places=12)
        self.assertLess(cross.loc[cross["symbol"].eq("S005"), "z_volatility"].iloc[0],
                        cross.loc[cross["symbol"].eq("S000"), "z_volatility"].iloc[0])

    def test_future_perturbation_cannot_change_past_scores(self):
        days = pd.bdate_range("2020-01-01", periods=50)
        prices = sample_prices(days)
        first = compute_factors(prices, members(prices), settings())
        changed = prices.copy()
        changed.loc[changed["date"] > days[30], ["adj_close", "volume"]] *= 7.0
        second = compute_factors(changed, members(prices), settings())
        pd.testing.assert_frame_equal(first.loc[first["date"] <= days[30]].reset_index(drop=True),
                                      second.loc[second["date"] <= days[30]].reset_index(drop=True))

    def test_missing_session_does_not_shorten_window(self):
        days = pd.bdate_range("2020-01-01", periods=45)
        prices = sample_prices(days)
        universe = members(prices)
        prices = prices.loc[~(prices["symbol"].eq("S000") & prices["date"].eq(days[15]))]
        factors = compute_factors(prices, universe, settings())
        bad = factors.loc[factors["symbol"].eq("S000") & factors["date"].eq(days[30])].iloc[0]
        self.assertTrue(pd.isna(bad["momentum"]))
        self.assertTrue(pd.isna(bad["volatility"]))
        self.assertTrue(pd.isna(bad["activity"]))
        good = factors.loc[factors["symbol"].eq("S000") & factors["date"].eq(days[40])].iloc[0]
        self.assertTrue(np.isfinite(good["composite"]))

    def test_constant_cross_section_and_ineligible_stock(self):
        days = pd.bdate_range("2020-01-01", periods=25)
        prices = sample_prices(days)
        prices["adj_close"] = prices["date"].map({d: 10 + i for i, d in enumerate(days)})
        prices["volume"] = 100.0
        universe = members(prices)
        universe.loc[universe["symbol"].eq("S005"), "eligible"] = False
        factors = compute_factors(prices, universe, settings())
        self.assertFalse(factors["symbol"].eq("S005").any())
        final = factors.loc[factors["date"].eq(days[-1])]
        np.testing.assert_array_equal(final["composite"].to_numpy(), 0.0)
        only_one = universe.copy()
        only_one["eligible"] = only_one["symbol"].eq("S000")
        self.assertTrue(compute_factors(prices, only_one, settings())["composite"].isna().all())

    def test_turnover_mode_uses_trailing_mean(self):
        days = pd.bdate_range("2020-01-01", periods=25)
        prices = sample_prices(days)
        prices["turnover"] = prices["date"].map({d: i / 1000 for i, d in enumerate(days)})
        factors = compute_factors(prices, members(prices), settings(activity_mode="turnover"))
        self.assertAlmostEqual(factors.loc[factors["date"].eq(days[-1]), "activity"].iloc[0], np.mean(np.arange(5, 25) / 1000))

    def test_configured_calendar_preserves_all_market_missing_day(self):
        days = pd.bdate_range("2020-01-01", periods=45)
        prices = sample_prices(days)
        universe = members(prices)
        prices = prices.loc[~prices["date"].eq(days[15])]
        cfg = settings(calendar_dates=[day.strftime("%Y-%m-%d") for day in days])
        factors = compute_factors(prices, universe, cfg)
        self.assertTrue(factors.loc[factors["date"].eq(days[30]), "composite"].isna().all())
        self.assertTrue(factors.loc[factors["date"].eq(days[40]), "composite"].notna().all())


class ResearchTests(unittest.TestCase):
    def test_labels_use_next_open_and_purge_split_boundaries(self):
        days = pd.bdate_range("2020-10-01", "2021-04-30")
        prices = sample_prices(days)
        factors = compute_factors(prices, members(prices), settings())
        labels = build_forward_labels(prices, factors, days, settings())
        row = labels.loc[labels["date"].eq(pd.Timestamp("2020-10-30"))].iloc[0]
        self.assertEqual(row["entry_date"], pd.Timestamp("2020-11-02"))
        self.assertEqual(row["exit_date"], pd.Timestamp("2020-12-01"))
        indexed = prices.set_index(["date", "symbol"])["adj_open"]
        expected = indexed.loc[(row["exit_date"], row["symbol"])] / indexed.loc[(row["entry_date"], row["symbol"])] - 1
        self.assertAlmostEqual(row["forward_return"], expected)
        self.assertFalse(labels["date"].isin(pd.to_datetime(["2020-11-30", "2020-12-31", "2021-03-31"])).any())
        for _, group in labels.groupby("split"):
            self.assertEqual(group["date"].dt.year.nunique(), 1)
            self.assertEqual(group["date"].dt.year.iloc[0], group["exit_date"].dt.year.iloc[0])

    def test_rank_ic_is_positive_one_and_groups_ordered(self):
        days = pd.bdate_range("2020-01-01", "2020-06-30")
        prices = sample_prices(days, n=10)
        factors = compute_factors(prices, members(prices), settings())
        # Assign explicit ordered scores, independent of any numerical tiny vol.
        factors["z_momentum"] = factors["symbol"].str[1:].astype(int).astype(float)
        results = analyze_factors(prices, factors, days, settings())
        ic = results["ic"].loc[results["ic"]["factor"].eq("momentum"), "ic"].dropna()
        self.assertGreater(len(ic), 0)
        np.testing.assert_allclose(ic, 1.0)
        groups = results["groups"].query("factor == 'momentum'")
        for _, cross in groups.groupby("date"):
            self.assertEqual(list(cross["group"]), [1, 2, 3, 4, 5])
            self.assertTrue(cross["forward_return"].is_monotonic_increasing)
        summary = results["ic_summary"].query("factor == 'momentum'").iloc[0]
        self.assertTrue(pd.isna(summary["icir"]))

    def test_constant_score_has_no_ic_or_fake_groups(self):
        days = pd.bdate_range("2020-01-01", "2020-06-30")
        prices = sample_prices(days)
        factors = compute_factors(prices, members(prices), settings())
        factors["z_activity"] = 0.0
        results = analyze_factors(prices, factors, days, settings())
        self.assertTrue(results["ic"].query("factor == 'activity'")["ic"].isna().all())
        self.assertTrue(results["groups"].query("factor == 'activity'").empty)

    def test_partial_last_month_is_not_a_signal(self):
        days = pd.bdate_range("2020-01-01", "2020-03-17")
        self.assertEqual(list(monthly_signal_dates(days)), list(pd.to_datetime(["2020-01-31", "2020-02-28"])))

    def test_missing_exit_is_dropped_not_filled(self):
        days = pd.bdate_range("2020-01-01", "2020-06-30")
        prices = sample_prices(days)
        factors = compute_factors(prices, members(prices), settings())
        prices.loc[prices["date"].eq(pd.Timestamp("2020-03-02")) & prices["symbol"].eq("S000"), "adj_open"] = np.nan
        labels = build_forward_labels(prices, factors, days, settings())
        self.assertFalse(((labels["date"] == pd.Timestamp("2020-01-31")) & labels["symbol"].eq("S000")).any())


if __name__ == "__main__":
    unittest.main()
