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
import numpy as np

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy_ctastrategy import CtaTemplate, CtaStrategyApp

from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.RegimeService import RegimeService


class EMTMultiFactorStrategy(CtaTemplate):
    """
    东方财富模拟盘 - 多因子策略（BOLL + CCI）
    """

    author = "Claude"

    # 策略参数
    buy_threshold = 0.5
    sell_threshold = -0.5
    fixed_size = 100  # 东方财富以股为单位
    stop_loss_pct = 0.03
    take_profit_pct = 0.08
    trailing_stop_pct = 0.02

    # 策略变量
    composite_score = 0.0
    entry_price = 0.0
    highest_price = 0.0

    parameters = ["buy_threshold", "sell_threshold", "fixed_size",
                  "stop_loss_pct", "take_profit_pct", "trailing_stop_pct"]
    variables = ["composite_score", "entry_price", "highest_price"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = None  # 用于K线生成器

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        self.load_bar(10)  # 加载10天历史数据

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_bar(self, bar: BarData):
        """K线推送"""
        # 这里需要实时计算因子得分
        # 实际使用时需要维护历史数据窗口
        pass


class EMTPaperTradingService:
    """
    东方财富模拟盘交易服务
    """

    def __init__(self):
        self.event_engine = None
        self.main_engine = None
        self.cta_engine = None

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
                "交易服务器": "120.27.164.69",   # 东方财富模拟交易服务器
                "交易端口": 6001,
                "行情路径": "",
                "交易路径": "",
                "授权码": ""
            }

            # 连接网关
            self.main_engine.connect(setting, "EMT")
            print("[连接] 正在连接东方财富模拟盘...")
            print(f"[账号] {account}")

        except ImportError:
            print("[错误] 未安装vnpy_emt模块")
            print("[提示] 请运行: pip install vnpy_emt")
            return False

        return True


if __name__ == '__main__':
    print("=" * 70)
    print("东方财富模拟盘接入示例")
    print("=" * 70)
    print("\n[步骤1] 注册东方财富模拟账号")
    print("  访问: https://www.18.cn/")
    print("  注册并获取模拟交易账号\n")

    print("[步骤2] 安装vnpy_emt模块")
    print("  运行: pip install vnpy_emt\n")

    print("[步骤3] 配置并连接")
    print("  修改下方代码中的账号密码\n")

    # 示例代码
    service = EMTPaperTradingService()
    service.init_engines()

    # TODO: 替换为你的东方财富模拟账号
    # service.connect_emt_gateway(
    #     account="your_account",
    #     password="your_password"
    # )

    print("=" * 70)
    print("配置完成后，取消注释上方代码即可连接模拟盘")
    print("=" * 70)

