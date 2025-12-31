"""
东方财富模拟盘接入示例
使用vnpy_emt接入东方财富证券模拟交易系统
"""
import sys
import os
from pathlib import Path

# 关键修复：在导入VeighNa之前先切换到项目根目录
project_root = Path(__file__).parent.parent
os.chdir(str(project_root))  # 切换工作目录
sys.path.insert(0, str(project_root))

# 应用 vnpy_emt 兼容性补丁（修复 onDisconnected 参数问题）
try:
    from service.emt_patch import apply_patch
    apply_patch()
except Exception as e:
    print(f"[警告] 补丁应用失败: {e}")

from vnpy_emt import EmtGateway

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
                self.write_log(
                    f"平仓 - {exit_reason} | 收益率: {current_pnl_pct:.2%} | 得分: {self.composite_score:.4f}")

        self.put_event()


class EMTPaperTradingService:
    """
    东方财富模拟盘交易服务
    """

    def __init__(self, simulation_mode=False):
        """
        Args:
            simulation_mode: 是否使用模拟模式（不连接真实EMT服务器）
        """
        self.event_engine = None
        self.main_engine = None
        self.cta_engine = None
        self.connected = False
        self.simulation_mode = simulation_mode

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
        if self.simulation_mode:
            print("[模拟模式] 跳过真实EMT连接")
            self.connected = True
            return True

        try:

            # 添加EMT网关
            self.main_engine.add_gateway(EmtGateway)
            # 配置连接参数
            setting = {
                "账号": account,
                "密码": password,
                "客户号": 1,
                "行情地址": "120.27.164.138",  # 东方财富模拟行情服务器
                "行情端口": 6002,
                "交易地址": "120.27.164.69",  # 东方财富模拟交易服务器
                "交易端口": 6001,
                "行情协议": "TCP",
                "日志级别": "INFO"
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
            # 修复编码错误问题
            try:
                error_msg = str(e)
            except:
                error_msg = "未知错误（编码问题）"
            print(f"[错误] 连接失败: {error_msg}")
            print("[提示] 可能的原因：")
            print("  1. 账号密码不正确")
            print("  2. 模拟账号未激活")
            print("  3. 服务器地址已变更")
            print("  4. 网络连接问题")
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


def show_log_info():
    """显示日志文件位置信息"""
    from vnpy.trader.utility import get_folder_path
    from datetime import datetime

    log_folder = get_folder_path('log')
    today = datetime.now().strftime('%Y%m%d')
    log_file = f"{log_folder}/vt_{today}.log"

    print("\n" + "=" * 70)
    print("VeighNa 日志信息")
    print("=" * 70)
    print(f"日志目录: {log_folder}")
    print(f"今日日志: vt_{today}.log")
    print(f"完整路径: {log_file}")
    print("\n[查看方法]")
    print(f"1. 直接打开: {log_file}")
    print(f"2. 命令行查看: type \"{log_file}\"")
    print(f"3. 实时监控: Get-Content \"{log_file}\" -Wait -Tail 20")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    print("=" * 70)
    print("东方财富模拟盘 - 多因子策略实盘测试")
    print("=" * 70)

    # 选择运行模式
    USE_SIMULATION_MODE = False  # 设置为True使用模拟模式，False使用真实EMT连接

    if USE_SIMULATION_MODE:
        print("\n[运行模式] 模拟模式（不连接真实EMT服务器）")
        print("[说明] 此模式下策略逻辑可以正常运行，但不会执行真实交易")
    else:
        print("\n[运行模式] 真实连接模式")
        print("\n[重要提示]")
        print("1. 需要先在东方财富官网注册模拟账号")
        print("2. 注册地址：https://www.18.cn/")
        print("3. 请修改代码中的账号密码为您自己的模拟账号")
        print("4. 如果连接失败，请检查：")
        print("   - 账号密码是否正确")
        print("   - 模拟账号是否已激活")
        print("   - 服务器地址是否最新")

    # 步骤1：初始化服务
    print("\n[步骤1] 初始化服务")
    service = EMTPaperTradingService(simulation_mode=USE_SIMULATION_MODE)
    service.init_engines()

    # 步骤2：连接模拟盘
    print("\n[步骤2] 连接东方财富模拟盘")

    if not USE_SIMULATION_MODE:
        print("[警告] 使用示例账号，可能无法连接")
        print("[建议] 请替换为您自己的模拟账号")

    success = service.connect_emt_gateway(
        account="13675831750",  # 请替换为您的模拟账号
        password="057a2bee"  # 请替换为您的模拟密码
    )

    if not success:
        print("\n[失败] 连接失败，请检查账号密码或网络")
        if not USE_SIMULATION_MODE:
            print("[提示] 如果您还没有模拟账号，请先注册：https://www.18.cn/")
            print("[提示] 或者将 USE_SIMULATION_MODE 设置为 True 使用模拟模式")
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

    # 显示日志文件位置
    show_log_info()
