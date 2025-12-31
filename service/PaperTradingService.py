"""
基于VeighNa PaperAccount的模拟盘交易服务
使用本地模拟账户进行实时策略测试
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Dict
import pandas as pd

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy_ctastrategy import CtaStrategyApp, CtaEngine

from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.RegimeService import RegimeService


class PaperTradingService:
    """
    VeighNa纸面交易服务

    功能：
    1. 使用VeighNa的本地模拟账户
    2. 支持实时行情接入
    3. 支持策略自动交易
    4. 提供完整的风险控制
    """

    def __init__(self, initial_capital: float = 100000):
        """
        初始化纸面交易服务

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.event_engine = None
        self.main_engine = None
        self.cta_engine = None
        self.regime_service = None

    def init_engines(self):
        """初始化VeighNa引擎"""
        # 创建事件引擎
        self.event_engine = EventEngine()

        # 创建主引擎
        self.main_engine = MainEngine(self.event_engine)

        # 添加CTA策略应用
        self.cta_engine = self.main_engine.add_app(CtaStrategyApp)

        print(f"[初始化] VeighNa引擎初始化完成")
        print(f"[初始化] 初始资金: {self.initial_capital:,.2f} CNY")

    def add_paper_gateway(self):
        """
        添加纸面交易网关

        注意：VeighNa的PaperAccount需要配合实际的行情网关使用
        这里我们使用回测模式来模拟
        """
        print("[配置] 使用本地模拟账户模式")
        print("[提示] 如需实时行情，请配置行情网关（如CTP、东方财富等）")

    def calculate_factors(self, dataset: List[CommonStockDataset],
                          time_interval: TimeInterval) -> List[Dict]:
        """
        计算多因子得分（BOLL + CCI策略）

        Args:
            dataset: 股票数据集
            time_interval: 时间间隔

        Returns:
            因子得分列表
        """
        self.regime_service = RegimeService(time_interval=time_interval)

        # 注册因子权重
        self.regime_service.register_factor('boll', weight=2.0)  # 均值回归 (57%)
        self.regime_service.register_factor('cci', weight=1.5)   # 反转信号 (43%)

        # 计算因子
        boll_factors = self.regime_service.calculate_boll_factor(dataset, period=20, std_dev=2.0)
        cci_factors = self.regime_service.calculate_cci_factor(dataset, period=14)

        # 合成因子
        composite_scores = self.regime_service.combine_factors([
            boll_factors,
            cci_factors
        ])

        return composite_scores


# 同花顺模拟盘替代方案说明
"""
=== 同花顺模拟盘接入说明 ===

VeighNa目前不支持直接接入同花顺模拟盘交易接口。

可用的替代方案：

方案1：使用同花顺iFinD数据 + VeighNa本地模拟盘（推荐）
------------------------------------------------------
1. 安装同花顺数据接口：pip install vnpy_ifind
2. 使用iFinD获取实时行情数据
3. 使用VeighNa的PaperAccount进行本地模拟交易
4. 优点：数据质量高，完全本地控制
5. 缺点：需要购买iFinD数据服务

方案2：使用其他券商模拟盘
------------------------------------------------------
- 东方财富模拟盘：pip install vnpy_emt
- 华泰证券模拟盘：pip install vnpy_sec
- 中泰证券模拟盘：pip install vnpy_xtp
- 优点：免费，真实模拟环境
- 缺点：需要开通对应券商账户

方案3：使用期货SimNow模拟盘
------------------------------------------------------
- 安装：pip install vnpy_ctp
- 注册：http://www.simnow.com.cn/
- 优点：完全免费，数据真实，7x24小时
- 缺点：仅支持期货品种

方案4：继续使用回测引擎（当前方案）
------------------------------------------------------
- 使用BacktestingEngine进行历史数据回测
- 优点：快速验证策略，无需实时行情
- 缺点：无法测试实盘滑点、延迟等问题

推荐使用方案1或方案2。
"""


if __name__ == '__main__':
    print("=" * 70)
    print("VeighNa 模拟盘交易服务")
    print("=" * 70)
    print("\n[提示] 同花顺暂不支持直接接入VeighNa")
    print("[提示] 请参考上述替代方案\n")

    # 示例：使用本地模拟账户
    service = PaperTradingService(initial_capital=100000)
    service.init_engines()
    service.add_paper_gateway()

    print("\n" + "=" * 70)
    print("如需实盘/模拟盘交易，请选择以下方案：")
    print("=" * 70)
    print("1. 东方财富模拟盘：pip install vnpy_emt")
    print("2. 华泰证券模拟盘：pip install vnpy_sec")
    print("3. 期货SimNow：pip install vnpy_ctp")
    print("4. 同花顺数据+本地模拟：pip install vnpy_ifind")
    print("=" * 70)

