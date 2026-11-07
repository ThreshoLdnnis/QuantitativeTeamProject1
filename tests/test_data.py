"""Dataset contracts protect input lineage and reject unsafe accounting data."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import numpy as np
import pandas as pd

from ashare_lab.config import load_config
from ashare_lab.data import (data_quality, load_dataset, save_dataset,
                             validate_dataset, write_database)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.calendar = pd.bdate_range("2020-01-02", "2020-01-06")
        self.prices = pd.DataFrame([
            dict(date=day, symbol=symbol, open=10.0, high=11.0, low=9.0,
                 close=10.5, adj_open=20.0, adj_close=21.0, volume=1000.0,
                 turnover=.01, can_buy=True, can_sell=True, status_known=True)
            for day in self.calendar for symbol in ["000001", "600000"]
        ])
        self.universe = self.prices[["date", "symbol"]].copy()
        self.universe["eligible"] = True
        self.metadata = dict(kind="synthetic", source="unit test fixture", limitations=["not real observations"])

    def validate(self, prices=None, universe=None, calendar=None):
        return validate_dataset(self.prices if prices is None else prices,
                                self.universe if universe is None else universe,
                                self.calendar if calendar is None else calendar)

    def test_csv_roundtrip_preserves_codes_flags_missing_turnover_and_metadata(self):
        self.prices.loc[0, "turnover"] = np.nan
        self.prices.loc[1, ["can_buy", "status_known"]] = False
        with tempfile.TemporaryDirectory() as temp:
            save_dataset(temp, self.prices, self.universe, self.calendar, self.metadata)
            prices, universe, calendar, metadata = load_dataset(temp)
        pd.testing.assert_frame_equal(prices.reset_index(drop=True), self.prices.reset_index(drop=True))
        pd.testing.assert_frame_equal(universe, self.universe)
        self.assertEqual(calendar.tolist(), self.calendar.tolist())
        self.assertEqual(metadata, self.metadata)
        self.assertEqual(prices.symbol.iloc[0], "000001")

    def test_duplicate_source_keys_are_rejected(self):
        for target in ["prices", "universe"]:
            with self.subTest(table=target):
                frame = getattr(self, target)
                kwargs = {target: pd.concat([frame, frame.iloc[:1]], ignore_index=True)}
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    self.validate(**kwargs)

    def test_missing_key_and_outside_calendar_are_rejected(self):
        bad = self.prices.copy()
        bad.loc[0, "symbol"] = None
        with self.assertRaisesRegex(ValueError, "missing keys"):
            self.validate(prices=bad)
        bad = self.prices.copy()
        bad.loc[0, "date"] = pd.Timestamp("2019-12-31")
        with self.assertRaisesRegex(ValueError, "outside trading calendar"):
            self.validate(prices=bad)

    def test_nonfinite_and_nonpositive_prices_are_rejected(self):
        for column, value in [("adj_open", np.inf), ("adj_close", np.nan), ("open", 0), ("low", -1)]:
            with self.subTest(column=column, value=value):
                bad = self.prices.copy()
                bad.loc[0, column] = value
                with self.assertRaises(ValueError):
                    self.validate(prices=bad)

    def test_raw_ohlc_ordering_is_checked_independently_of_adjusted_prices(self):
        bad = self.prices.copy()
        bad.loc[0, "high"] = 9
        with self.assertRaisesRegex(ValueError, "OHLC"):
            self.validate(prices=bad)

    def test_negative_volume_turnover_and_false_executable_suspension_rejected(self):
        for column, value in [("volume", -1), ("turnover", -.001), ("volume", 0)]:
            with self.subTest(column=column, value=value):
                bad = self.prices.copy()
                bad.loc[0, column] = value
                with self.assertRaises(ValueError):
                    self.validate(prices=bad)
        suspended = self.prices.copy()
        suspended.loc[0, ["volume", "can_buy", "can_sell"]] = [0, False, False]
        self.validate(prices=suspended)

    def test_missing_eligible_rows_and_unknown_status_are_disclosed(self):
        incomplete = self.prices.iloc[1:].copy()
        incomplete.loc[incomplete.index[0], "status_known"] = False
        self.validate(prices=incomplete)
        quality = data_quality(incomplete, self.universe, self.calendar, self.metadata)
        self.assertEqual(quality["missing_eligible_rows"], 1)
        self.assertEqual(quality["unknown_status_rows"], 1)
        self.assertGreaterEqual(len(quality["limitations"]), 3)

    def test_csv_unknown_boolean_strings_do_not_become_truthy(self):
        with tempfile.TemporaryDirectory() as temp:
            save_dataset(temp, self.prices, self.universe, self.calendar, self.metadata)
            path = Path(temp) / "prices.csv"
            rows = pd.read_csv(path, dtype={"symbol": str})
            rows["can_buy"] = rows["can_buy"].astype(str)
            rows.loc[0, "can_buy"] = "unknown"
            rows.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "can_buy"):
                load_dataset(temp)

    def test_validation_calendar_rejects_duplicate_nat_and_intraday_labels(self):
        for calendar in [self.calendar.insert(0, self.calendar[0]),
                         self.calendar.insert(0, pd.NaT),
                         self.calendar.append(pd.DatetimeIndex([pd.Timestamp("2020-01-07 12:00")]))]:
            with self.subTest(calendar=calendar.tolist()):
                with self.assertRaises(ValueError):
                    self.validate(calendar=calendar)

    def test_numeric_string_api_input_is_handled_with_validation_error_or_conversion(self):
        text_prices = self.prices.copy()
        columns = ["open", "high", "low", "close", "adj_open", "adj_close", "volume", "turnover"]
        for column in columns:
            text_prices[column] = text_prices[column].astype(str)
        # Either explicit rejection or acceptance is a valid contract. A leaked
        # TypeError from arithmetic on strings is not an intentional rejection.
        try:
            self.validate(prices=text_prices)
        except ValueError:
            pass

    def test_sqlite_schema_iso_dates_and_unique_keys(self):
        factors = self.prices[["date", "symbol"]].copy()
        factors["composite"] = 0.0
        positions = self.prices[["date", "symbol"]].copy()
        positions["strategy"] = "multi"
        positions["quantity"] = 1.0
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "research.sqlite"
            write_database(db, self.prices, self.universe, self.calendar, factors, positions)
            with closing(sqlite3.connect(db)) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertTrue({"stock_prices", "stock_universe", "trading_calendar", "factor_values", "portfolio_positions"}.issubset(tables))
                self.assertEqual(conn.execute("SELECT symbol,date,can_buy FROM stock_prices ORDER BY date,symbol LIMIT 1").fetchone(),
                                 ("000001", "2020-01-02", 1))
                for table in ["stock_prices", "stock_universe", "trading_calendar", "factor_values", "portfolio_positions"]:
                    with self.subTest(table=table):
                        with self.assertRaises(sqlite3.IntegrityError):
                            conn.execute(f"INSERT INTO {table} SELECT * FROM {table} LIMIT 1")
                        conn.rollback()


class ConfigTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "configs" / "baseline.json"
        self.config = json.loads(path.read_text(encoding="utf-8"))

    def load(self, cfg):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            return load_config(path)

    def test_baseline_validates_and_overlapping_splits_fail(self):
        self.assertEqual(self.load(self.config), self.config)
        bad = copy.deepcopy(self.config)
        bad["splits"]["validation"][0] = "2022-12-31"
        with self.assertRaises(ValueError):
            self.load(bad)

    def test_nonfinite_parameters_and_nat_boundaries_are_rejected(self):
        for key, value in [("initial_cash", np.nan), ("initial_cash", np.inf),
                           ("cost_multipliers", [0, np.inf]), ("cost_multipliers", [np.nan]),
                           ("start", "NaT"), ("end", "NaT")]:
            with self.subTest(key=key, value=value):
                bad = copy.deepcopy(self.config)
                bad[key] = value
                with self.assertRaises(ValueError):
                    self.load(bad)
        bad = copy.deepcopy(self.config)
        bad["splits"]["development"][0] = "NaT"
        with self.assertRaises(ValueError):
            self.load(bad)


if __name__ == "__main__":
    unittest.main()
