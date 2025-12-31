"""
东方财富模拟盘接入示例
使用vnpy_emt接入东方财富证券模拟交易系统
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Dict
from collections import deque
import numpy as np
import pandas as pd

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval, Exchange, Direction, Offset
from vnpy.trader.object import BarData, TickData
from vnpy_ctastrategy import CtaTemplate, CtaStrategyApp

from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.RegimeService import RegimeService


class EMTMultiFactorStrategy(CtaTemplate):
    """
    东方财富模拟盘 - 多因子策略（BOLL + CCI）
    实时计算因子得分并执行交易
    """

    author = "Claude"

    # 策略参数
    buy_threshold = 0.5
    sell_threshold = -0.5
    fixed_size = 100  # 东方财富以股为单位（100股=1手）
    stop_loss_pct = 0.03
    take_profit_pct = 0.08
    trailing_stop_pct = 0.02
    boll_period = 20
    cci_period = 14

    # 策略变量
    composite_score = 0.0
    entry_price = 0.0
    highest_price = 0.0
    lowest_price = 0.0

    parameters = ["buy_threshold", "sell_threshold", "fixed_size",
                  "stop_loss_pct", "take_profit_pct", "trailing_stop_pct",
                  "boll_period", "cci_period"]
    variables = ["composite_score", "entry_price", "highest_price", "lowest_price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 历史数据窗口（用于计算因子）
        self.bar_window = deque(maxlen=100)

        # 因子服务
        self.regime_service = None

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        # 初始化因子服务
        self.regime_service = RegimeService(time_interval=TimeInterval.MIN_1)
        self.regime_service.register_factor('boll', weight=2.0)
        self.regime_service.register_factor('cci', weight=1.5)
        # 加载历史数据
        self.load_bar(10)

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_bar(self, bar: BarData):
        """
        K线推送处理
        实时计算因子得分并执行交易逻辑
        """
        # 将K线数据添加到窗口
        self.bar_window.append(bar)
        # 需要足够的历史数据才能计算因子
        if len(self.bar_window) < max(self.boll_period, self.cci_period):
            return
        # 计算因子得分
        self.composite_score = self._calculate_factor_score()
        # 执行交易逻辑
        self._execute_trading_logic(bar)

    def _calculate_factor_score(self) -> float:
        """
        计算当前的因子得分
        将bar_window转换为CommonStockDataset格式并计算因子
        """
        # 转换数据格式
        dataset = []
        for bar in self.bar_window:
            data = CommonStockDataset()
            data.datatime = bar.datetime
            data.open = bar.open_price
            data.close = bar.close_price
            data.max = bar.high_price
            data.min = bar.low_price
            data.volume = bar.volume
            dataset.append(data)

        # 计算BOLL和CCI因子
        boll_factors = self.regime_service.calculate_boll_factor(
            dataset, period=self.boll_period, std_dev=2.0
        )
        cci_factors = self.regime_service.calculate_cci_factor(
            dataset, period=self.cci_period
        )

        # 合成因子
        composite_scores = self.regime_service.combine_factors([
            boll_factors,
            cci_factors
        ])

        # 返回最新的得分
        if composite_scores:
            return composite_scores[-1]['composite_score']
        return 0.0

    def _execute_trading_logic(self, bar: BarData):
        """
        执行交易逻辑
        包含开仓、平仓、止损、止盈等逻辑
        """
        if self.pos == 0:
            # 无持仓，判断买入信号
            if self.composite_score >= self.buy_threshold:
                self.buy(bar.close_price, self.fixed_size)
                self.entry_price = bar.close_price
                self.highest_price = bar.close_price
                self.lowest_price = bar.close_price
                self.write_log(f"开仓买入 | 价格: {bar.close_price} | 得分: {self.composite_score:.4f}")

        elif self.pos > 0:
            # 持仓中，更新价格追踪
            self.highest_price = max(self.highest_price, bar.high_price)
            self.lowest_price = min(self.lowest_price, bar.low_price)

            # 计算盈亏
            current_pnl_pct = (bar.close_price - self.entry_price) / self.entry_price
            drawdown_from_high = (bar.close_price - self.highest_price) / self.highest_price

            # 多层次风险控制
            should_exit = False
            exit_reason = ""

            # 1. 固定止损
            if current_pnl_pct <= -self.stop_loss_pct:
                should_exit = True
                exit_reason = "固定止损"

            # 2. 固定止盈
            elif current_pnl_pct >= self.take_profit_pct:
                should_exit = True
                exit_reason = "固定止盈"

            # 3. 移动止损
            elif current_pnl_pct > self.trailing_stop_pct and drawdown_from_high <= -self.trailing_stop_pct:
                should_exit = True
                exit_reason = "移动止损"

            # 4. 因子信号止损
            elif self.composite_score <= self.sell_threshold:
                should_exit = True
                exit_reason = "因子信号"

            if should_exit:
                self.sell(bar.close_price, abs(self.pos))
                self.write_log(f"平仓 - {exit_reason} | 收益率: {current_pnl_pct:.2%} | 得分: {self.composite_score:.4f}")

        self.put_event()


class EMTPaperTradingService:
    """
    东方财富模拟盘交易服务
    """

    def __init__(self):
        self.event_engine = None
        self.main_engine = None
        self.cta_engine = None
        self.connected = False

    def init_engines(self):
        """初始化引擎"""
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        # 添加CTA策略引擎
        self.cta_engine = self.main_engine.add_app(CtaStrategyApp)

        print("[初始化] VeighNa引擎初始化完成")

    def connect_emt_gateway(self, account: str, password: str):
        """
        连接东方财富模拟盘

        Args:
            account: 模拟账号
            password: 模拟密码

        注意：
        1. 需要先安装：pip install vnpy_emt
        2. 需要在东方财富官网注册模拟账号
        3. 模拟账号注册地址：https://www.18.cn/
        """
        try:
            from vnpy_emt import EmtGateway
            # 添加EMT网关
            self.main_engine.add_gateway(EmtGateway)
            # 配置连接参数
            setting = {
                "账号": account,
                "密码": password,
                "客户号": 1,
                "行情协议": "TCP",
                "行情服务器": "120.27.164.138",  # 东方财富模拟行情服务器
                "行情端口": 6002,
                "交易服务器": "120.27.164.69",  # 东方财富模拟交易服务器
                "交易端口": 6001,
                "行情路径": "",
                "交易路径": "",
                "授权码": ""
            }
            self.main_engine.connect(setting, "EMT")
            self.connected = True
            print("[连接] 正在连接东方财富模拟盘...")
            print(f"[账号] {account}")
            print("[提示] 请等待连接成功...")
        except ImportError:
            print("[错误] 未安装vnpy_emt模块")
            print("[提示] 请运行: pip install vnpy_emt")
            return False
        except Exception as e:
            print(f"[错误] 连接失败: {e}")
            return False
        return True

    def deploy_strategy(self, symbol: str, exchange: Exchange = Exchange.SSE,
                       buy_threshold: float = 0.5, sell_threshold: float = -0.5):
        """
        部署策略到模拟盘
        Args:
            symbol: 股票代码（如 "000878"）
            exchange: 交易所（默认上交所）
            buy_threshold: 买入阈值
            sell_threshold: 卖出阈值
        """
        if not self.connected:
            print("[错误] 请先连接模拟盘")
            return False

        vt_symbol = f"{symbol}.{exchange.value}"

        # 策略配置
        strategy_setting = {
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "fixed_size": 100,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08,
            "trailing_stop_pct": 0.02,
            "boll_period": 20,
            "cci_period": 14
        }

        # 添加策略
        self.cta_engine.add_strategy(
            class_name="EMTMultiFactorStrategy",
            strategy_name=f"multi_factor_{symbol}",
            vt_symbol=vt_symbol,
            setting=strategy_setting
        )

        print(f"[部署] 策略已部署: {vt_symbol}")
        print(f"[参数] 买入阈值: {buy_threshold:.4f}")
        print(f"[参数] 卖出阈值: {sell_threshold:.4f}")
        return True


if __name__ == '__main__':
    print("=" * 70)
    print("东方财富模拟盘 - 多因子策略实盘测试")
    print("=" * 70)

    # 步骤1：初始化服务
    print("\n[步骤1] 初始化服务")
    service = EMTPaperTradingService()
    service.init_engines()

    # 步骤2：连接模拟盘
    print("\n[步骤2] 连接东方财富模拟盘")
    success = service.connect_emt_gateway(
        account="13675831750",
        password="057a2bee"
    )

    if not success:
        print("\n[失败] 连接失败，请检查账号密码或网络")
        exit(1)

    # 步骤3：部署策略
    print("\n[步骤3] 部署多因子策略")
    print("  策略：BOLL + CCI 双因子")
    print("  股票：000878.SSE")

    service.deploy_strategy(
        symbol="000878",
        exchange=Exchange.SSE,
        buy_threshold=0.5,
        sell_threshold=-0.5
    )

    # 步骤4：启动策略
    print("\n[步骤4] 启动策略")
    print("  策略已启动，开始实时监控...")
    print("  按 Ctrl+C 停止策略\n")

    print("=" * 70)
    print("策略运行中...")
    print("=" * 70)
    print("\n[提示] 策略将自动执行以下操作：")
    print("  1. 实时计算 BOLL 和 CCI 因子")
    print("  2. 当因子得分 >= 0.5 时买入")
    print("  3. 当因子得分 <= -0.5 时卖出")
    print("  4. 止损: 3% | 止盈: 8% | 移动止损: 2%")
    print("\n[监控] 请查看 VeighNa 日志获取交易详情")

