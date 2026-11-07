-- 在 runs/demo/research.sqlite 或 runs/market_teaching/research.sqlite 中执行。
-- SQLite 表中的 date 为 ISO 日期字符串，symbol 为字符串。
-- 每段均可单独执行。先预测结果，再查看数据。

-- 1. SELECT + WHERE：查看一只股票的历史行情。
-- demo 的股票代码以实际数据库为准，先执行下一个 DISTINCT 查询。
SELECT DISTINCT symbol FROM stock_prices ORDER BY symbol LIMIT 10;
SELECT date, symbol, open, close, adj_close, volume
FROM stock_prices
WHERE symbol = (SELECT MIN(symbol) FROM stock_prices)
  AND date BETWEEN '2020-01-01' AND '2020-02-15'
ORDER BY date;

-- 2. GROUP BY：统计股票覆盖区间，识别不同股票样本长度。
SELECT symbol, COUNT(*) AS rows_count,
       MIN(date) AS first_date, MAX(date) AS last_date,
       SUM(CASE WHEN status_known = 0 THEN 1 ELSE 0 END) AS unknown_status_rows
FROM stock_prices
GROUP BY symbol
ORDER BY rows_count, symbol;

-- 3. 检查重复主键；正确结果为零行，不是删除重复记录。
SELECT date, symbol, COUNT(*) AS n
FROM stock_prices
GROUP BY date, symbol
HAVING COUNT(*) > 1;

-- 4. JOIN：仅查询当日股票池中合格的行情。
SELECT p.date, p.symbol, p.adj_close, u.eligible
FROM stock_prices AS p
JOIN stock_universe AS u
  ON p.date = u.date AND p.symbol = u.symbol
WHERE u.eligible = 1 AND p.date = '2020-02-03'
ORDER BY p.symbol;

-- 5. 每日覆盖检查：不能把单只股票没行情理解为全市场休市。
SELECT c.date, COUNT(p.symbol) AS price_rows
FROM trading_calendar AS c
LEFT JOIN stock_prices AS p ON c.date = p.date
WHERE c.date BETWEEN '2020-01-01' AND '2020-01-31'
GROUP BY c.date
ORDER BY c.date;

-- 6. 窗口函数：LAG 是历史值；不把 LEAD 未来收益放进因子。
-- 提醒：本例按已有记录位移，遇到缺失交易日可能跨过缺口。
-- 正式因子必须先对齐独立交易日历，使用 Python 参考实现核验。
WITH history AS (
  SELECT date, symbol, adj_close,
         LAG(adj_close, 20) OVER (PARTITION BY symbol ORDER BY date) AS lag20
  FROM stock_prices
)
SELECT date, symbol, adj_close / lag20 - 1.0 AS momentum20
FROM history
WHERE lag20 > 0 AND date BETWEEN '2020-01-01' AND '2020-02-15'
ORDER BY symbol, date;

-- 7. 查看某日因子评分；不能把未来标签 JOIN 进选股排序。
SELECT date, symbol, momentum, volatility, activity,
       z_momentum, z_volatility, z_activity, composite
FROM factor_values
WHERE date = (SELECT MAX(date) FROM factor_values
              WHERE date BETWEEN '2023-01-01' AND '2023-01-31')
  AND composite IS NOT NULL
ORDER BY composite DESC, symbol
LIMIT 10;

-- 8. 因子有效值覆盖；NULL 不等于零。
SELECT date, COUNT(*) AS rows_count,
       COUNT(momentum) AS momentum_count,
       COUNT(volatility) AS volatility_count,
       COUNT(activity) AS activity_count,
       COUNT(composite) AS composite_count
FROM factor_values
GROUP BY date
ORDER BY date
LIMIT 40;

-- 9. 检查持仓的估值恒等式；此表只包含持仓，不包含现金。
-- equity 和 cash 请与对应策略的 daily_*.csv 联合核对。
SELECT date, strategy, COUNT(*) AS holdings,
       SUM(market_value) AS invested_value,
       SUM(weight) AS invested_weight,
       MAX(ABS(market_value - quantity * close)) AS largest_valuation_error
FROM portfolio_positions
GROUP BY date, strategy
ORDER BY date, strategy
LIMIT 30;

-- 练习：解释为什么有时 invested_weight < 1，以及为何不能强制归一化为 1。
-- 练习：改写第 4 条，找出当日合格但没有行情的股票，调查原因。
-- 练习：对照 Python 结果解释第 6 条在缺失交易日情况下的风险。
