"""
基于VeighNa框架的回测服务
"""
import sys
from pathlib import Path

from service.fetch.SystemConvertService import SystemConvertService

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Dict
import pandas as pd
import numpy as np

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy_ctastrategy import CtaTemplate
from vnpy_ctastrategy.backtesting import BacktestingEngine

from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.RegimeService import RegimeService


class MultiFactorStrategy(CtaTemplate):
    """多因子量化策略"""

    author = "Claude"

    # 策略参数
    buy_threshold = 0.5
    sell_threshold = -0.5
    fixed_size = 1
    stop_loss_pct = 0.05
    take_profit_pct = 0.10

    # 策略变量
    composite_score = 0.0
    entry_price = 0.0
    highest_price = 0.0

    parameters = ["buy_threshold", "sell_threshold", "fixed_size", "stop_loss_pct", "take_profit_pct"]
    variables = ["composite_score", "entry_price", "highest_price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.factor_scores = setting.get('_factor_scores', {})

    def on_init(self):
        self.write_log("策略初始化")

    def on_start(self):
        self.write_log("策略启动")

    def on_stop(self):
        self.write_log("策略停止")

    def on_bar(self, bar: BarData):
        """K线数据推送"""
        # 获取当前时间点的因子得分
        self.composite_score = self.factor_scores.get(bar.datetime, 0.0)
        if self.pos == 0:
            # 无持仓，判断买入信号
            if self.composite_score >= self.buy_threshold:
                self.buy(bar.close_price, self.fixed_size)
                self.entry_price = bar.close_price
                self.highest_price = bar.close_price

        elif self.pos > 0:
            # 更新持仓期间最高价
            self.highest_price = max(self.highest_price, bar.high_price)
            current_pnl_pct = (bar.close_price - self.entry_price) / self.entry_price
            trailing_stop_pct = (bar.close_price - self.highest_price) / self.highest_price

            # 止损
            if current_pnl_pct <= -self.stop_loss_pct:
                self.sell(bar.close_price, abs(self.pos))
            # 止盈
            elif current_pnl_pct >= self.take_profit_pct:
                self.sell(bar.close_price, abs(self.pos))
            # 移动止损
            elif trailing_stop_pct <= -self.stop_loss_pct / 2:
                self.sell(bar.close_price, abs(self.pos))
            # 因子信号卖出
            elif self.composite_score <= self.sell_threshold:
                self.sell(bar.close_price, abs(self.pos))

        self.put_event()


class VeighNaBackTestService:
    """VeighNa回测服务"""

    def __init__(self):
        self.engine = BacktestingEngine()
        self.regime_service = None
        self.composite_scores = []

    def setup_backtest(self, symbol: str, exchange: Exchange, interval: Interval,
                       start: datetime, end: datetime, rate: float = 0.0003,
                       slippage: float = 0.0, size: int = 100,
                       pricetick: float = 0.01, capital: int = 100000):
        """配置回测参数"""
        self.engine.set_parameters(
            vt_symbol=f"{symbol}.{exchange.value}",
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital
        )

    def calculate_factors(self, dataset: List[CommonStockDataset],
                          time_interval: TimeInterval,
                          factor_config: Dict = None) -> List[Dict]:
        """计算多因子得分"""
        self.regime_service = RegimeService(time_interval=time_interval)
        if factor_config is None:
            factor_config = {
                'macd': {'weight': 2.0, 'period': 20},
                'rsi': {'weight': 1.5, 'period': 14},
                'momentum': {'weight': 1.0, 'period': 20},
                'volatility': {'weight': 1.0, 'period': 20}
            }
        # 注册因子
        for factor_name, config in factor_config.items():
            self.regime_service.register_factor(factor_name, weight=config['weight'])
        # 计算因子
        factor_results = []
        for factor_name, config in factor_config.items():
            if factor_name == 'macd':
                factor_results.append(
                    self.regime_service.calculate_macd(dataset, period=config['period']))
            elif factor_name == 'rsi':
                factor_results.append(
                    self.regime_service.calculate_rsi_factor(dataset, period=config['period']))
            elif factor_name == 'momentum':
                factor_results.append(
                    self.regime_service.calculate_momentum_factor(dataset, period=config['period']))
            elif factor_name == 'volatility':
                factor_results.append(
                    self.regime_service.calculate_volatility_factor(dataset, period=config['period']))

        self.composite_scores = self.regime_service.combine_factors(factor_results)
        return self.composite_scores

    # core核心回测方法
    def run_backtest(self, dataset: List[CommonStockDataset], strategy_class, setting: dict) -> pd.DataFrame:
        """运行回测"""
        if self.composite_scores:
            # 将字符串datetime转换为datetime对象作为键
            scores_dict = {}
            for score in self.composite_scores:
                dt = score['datatime']
                if isinstance(dt, str):
                    dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                scores_dict[dt] = score['composite_score']
            setting['_factor_scores'] = scores_dict

        # 将指定的策略类和参数设置添加到回测引擎中
        self.engine.history_data = dataset
        self.engine.add_strategy(strategy_class, setting)
        # 执行实际的回测过程
        self.engine.run_backtesting()
        # 计算并返回回测结果
        return self.engine.calculate_result()

    def get_trade_statistics(self) -> Dict:
        """获取交易统计"""
        trades = self.engine.trades
        if not trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0.0, 'avg_profit': 0.0, 'avg_loss': 0.0,
                'profit_factor': 0.0, 'total_profit': 0.0, 'total_loss': 0.0
            }

        winning_trades = [t.pnl for t in trades.values() if hasattr(t, 'pnl') and t.pnl > 0]
        losing_trades = [t.pnl for t in trades.values() if hasattr(t, 'pnl') and t.pnl < 0]

        total_trades = len(trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        total_profit = sum(winning_trades) if winning_trades else 0.0
        total_loss = abs(sum(losing_trades)) if losing_trades else 0.0

        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_count / total_trades if total_trades > 0 else 0.0,
            'avg_profit': total_profit / win_count if win_count > 0 else 0.0,
            'avg_loss': total_loss / loss_count if loss_count > 0 else 0.0,
            'profit_factor': total_profit / total_loss if total_loss > 0 else 0.0,
            'total_profit': total_profit,
            'total_loss': total_loss
        }


if __name__ == '__main__':

    from service.fetch.SystemFetchDataset import SystemFetchDataset

    print("=== VeighNa Multi-Factor Backtest System ===\n")
    # 获取数据
    try:
        fetch = SystemFetchDataset()
        datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
        print(f"[OK] Data loaded: {len(datasets)} bars\n")
    except Exception as e:
        print(f"[ERROR] Data fetch failed: {e}")
        exit(1)
    # 初始化回测服务
    backtest_service = VeighNaBackTestService()

    # 配置回测参数
    print("[Step 1] Configure Backtest")
    backtest_service.setup_backtest(
        symbol="000878",
        exchange=Exchange.SSE,
        interval=Interval.MINUTE,
        start=datetime(2025, 12, 25, 9, 30),
        end=datetime(2025, 12, 25, 15, 0),
        rate=0.0003,
        slippage=0.01,
        size=100,
        pricetick=0.01,
        capital=100000
    )
    print("  - Symbol: 000878 | Capital: 100,000 CNY\n")

    # 加载数据
    print("[Step 2] Load Data")
    convert = SystemConvertService()
    bars = convert.dataset_convert_bars(datasets, "000878", Exchange.SSE)
    print(f"  - Loaded {len(bars)} bars\n")

    # 计算因子
    print("[Step 3] Calculate Factors")
    time_interval = TimeInterval.from_period(1)
    composite_scores = backtest_service.calculate_factors(datasets, time_interval)
    scores_array = np.array([s['composite_score'] for s in composite_scores])
    print(f"  - Scores: Min={scores_array.min():.4f}, Max={scores_array.max():.4f}, Mean={scores_array.mean():.4f}\n")

    # 运行回测
    print("[Step 4] Run Backtest")
    buy_threshold = np.percentile(scores_array, 70)
    sell_threshold = np.percentile(scores_array, 30)

    strategy_setting = {
        "buy_threshold": float(buy_threshold),
        "sell_threshold": float(sell_threshold),
        "fixed_size": 1,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.10
    }
    print(f"  - Buy Threshold: {buy_threshold:.4f} | Sell Threshold: {sell_threshold:.4f}\n")

    result = backtest_service.run_backtest(bars, MultiFactorStrategy, strategy_setting)

    # 输出结果
    print("=" * 60)
    print("[Backtest Results]")
    print("=" * 60)

    if isinstance(result, pd.DataFrame) and not result.empty:
        last_row = result.iloc[-1]

        print(f"\n>> Profit Metrics:")
        print(f"  Total PnL:        {last_row.get('total_pnl', 0):>12.2f} CNY")
        print(f"  Net PnL:          {last_row.get('net_pnl', 0):>12.2f} CNY")
        print(f"  Total Return:     {last_row.get('total_return', 0):>12.2%}")
        print(f"  Annual Return:    {last_row.get('annual_return', 0):>12.2%}")
        print(f"  Daily Return:     {last_row.get('daily_return', 0):>12.2%}")

        print(f"\n>> Trade Statistics:")
        actual_trades = len(backtest_service.engine.trades)
        print(f"  Total Trades:     {actual_trades:>12}")
        print(f"  Total Orders:     {last_row.get('total_trades', 0):>12.0f}")
        print(f"  Winning Trades:   {last_row.get('winning_trades', 0):>12.0f}")
        print(f"  Losing Trades:    {last_row.get('losing_trades', 0):>12.0f}")
        print(f"  Win Rate:         {last_row.get('win_rate', 0):>12.2%}")

        print(f"\n>> Profit/Loss Analysis:")
        print(f"  Avg Winning:      {last_row.get('avg_winning_trade', 0):>12.2f} CNY")
        print(f"  Avg Losing:       {last_row.get('avg_losing_trade', 0):>12.2f} CNY")
        print(f"  Profit/Loss Ratio:{last_row.get('profit_loss_ratio', 0):>12.2f}")

        print(f"\n>> Risk Metrics:")
        print(f"  Max Drawdown:     {last_row.get('max_drawdown', 0):>12.2%}")
        print(f"  Max DD Percent:   {last_row.get('max_ddpercent', 0):>12.2%}")
        print(f"  Sharpe Ratio:     {last_row.get('sharpe_ratio', 0):>12.2f}")

        print(f"\n>> Complete Statistics:")
        print(result.to_string())
    else:
        print("\n[WARN] No valid results generated")

    print("\n" + "=" * 60)
    print("Backtest Completed!")
    print("=" * 60)
