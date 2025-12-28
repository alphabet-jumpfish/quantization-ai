import sys
from pathlib import Path

from service.fetch.SystemPlateFetchService import SystemPlateFetchService

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import akshare as ak

from entity.PlateDataset import PlateDataset, PlateStockInfo


class PlateMomentumResult:
    """板块动量分析结果"""

    def __init__(self, plate_name: str, datatime: datetime, momentum_score: float,
                 avg_change_pct: float, up_stock_ratio: float, total_stocks: int):
        self.plate_name = plate_name
        self.datatime = datatime
        self.momentum_score = momentum_score  # 动量得分 [-1, 1]
        self.avg_change_pct = avg_change_pct  # 平均涨跌幅
        self.up_stock_ratio = up_stock_ratio  # 上涨股票占比
        self.total_stocks = total_stocks  # 板块内股票总数

    def __repr__(self):
        return (f"PlateMomentumResult(plate={self.plate_name}, "
                f"momentum={self.momentum_score:.4f}, "
                f"avg_change={self.avg_change_pct:.2f}%, "
                f"up_ratio={self.up_stock_ratio:.2f}%)")


class PlateMomentumService:
    """板块动量服务"""

    def __init__(self):
        self.plate_cache = {}  # 缓存板块数据

    def get_plate_stocks(self, plate_name: str) -> List[PlateStockInfo]:
        """
        获取指定板块的成分股信息
        Args:
            plate_name: 板块名称
        Returns:
            成分股信息列表
        """
        try:
            # 从缓存中获取
            if plate_name in self.plate_cache:
                return self.plate_cache[plate_name]
            # 获取板块成分股
            _plate_fetch = SystemPlateFetchService()
            stocks_info = _plate_fetch.get_plate_stocks(plate_name=plate_name)
            # 缓存结果
            self.plate_cache[plate_name] = stocks_info
            return stocks_info
        except Exception as e:
            print(f"获取板块 {plate_name} 成分股失败: {e}")
            return []

    def calculate_plate_momentum(self, plate_name: str) -> Optional[PlateMomentumResult]:
        """
        计算单个板块的动量得分
        Args:
            plate_name: 板块名称
        Returns:
            板块动量分析结果
        """
        stocks_info = self.get_plate_stocks(plate_name)

        if not stocks_info:
            return None

        # 提取涨跌幅数据
        change_pcts = [stock['change_pct'] for stock in stocks_info]

        # 计算统计指标
        avg_change_pct = np.mean(change_pcts)
        up_stocks = sum(1 for pct in change_pcts if pct > 0)
        up_stock_ratio = (up_stocks / len(stocks_info)) * 100

        # 计算动量得分
        # 综合考虑：平均涨跌幅 + 上涨股票占比
        momentum_score = self._calculate_momentum_score(
            avg_change_pct, up_stock_ratio, change_pcts
        )

        return PlateMomentumResult(
            plate_name=plate_name,
            datatime=datetime.now(),
            momentum_score=momentum_score,
            avg_change_pct=avg_change_pct,
            up_stock_ratio=up_stock_ratio,
            total_stocks=len(stocks_info)
        )

    def _calculate_momentum_score(self, avg_change_pct: float,
                                  up_stock_ratio: float,
                                  change_pcts: List[float]) -> float:
        """
        计算动量得分 [-1, 1]
        Args:
            avg_change_pct: 平均涨跌幅
            up_stock_ratio: 上涨股票占比
            change_pcts: 所有股票涨跌幅列表
        Returns:
            动量得分
        """
        # 1. 平均涨跌幅得分 (权重 0.4)
        # 假设 ±10% 为极值
        change_score = np.clip(avg_change_pct / 10.0, -1.0, 1.0)

        # 2. 上涨股票占比得分 (权重 0.3)
        # 50% 为中性，转换为 [-1, 1]
        ratio_score = (up_stock_ratio - 50) / 50.0

        # 3. 涨跌幅一致性得分 (权重 0.3)
        # 标准差越小，一致性越高
        std_dev = np.std(change_pcts)
        consistency_score = 1.0 / (1.0 + std_dev)  # 标准差越小，得分越高
        if avg_change_pct < 0:
            consistency_score = -consistency_score

        # 综合得分
        momentum_score = (0.4 * change_score +
                          0.3 * ratio_score +
                          0.3 * consistency_score)

        return np.clip(momentum_score, -1.0, 1.0)

    def analyze_all_plates(self, top_n: int = 10) -> List[PlateMomentumResult]:
        """
        分析所有板块的动量，返回排名前N的板块
        Args:
            top_n: 返回前N个板块
        Returns:
            板块动量结果列表（按动量得分降序）
        """
        _plate_fetch = SystemPlateFetchService()
        plate_df = _plate_fetch.get_plate_list()

        if plate_df.empty:
            return []

        results = []
        total_plates = len(plate_df)

        print(f"\n=== 开始分析 {total_plates} 个板块 ===")

        for idx, row in plate_df.iterrows():
            plate_name = row['板块名称']
            print(f"[{idx + 1}/{total_plates}] 分析板块: {plate_name}")

            result = self.calculate_plate_momentum(plate_name)
            if result:
                results.append(result)

        # 按动量得分降序排序
        results.sort(key=lambda x: x.momentum_score, reverse=True)

        print(f"\n=== 分析完成，共 {len(results)} 个板块 ===")

        return results[:top_n]

    def get_top_stocks_in_plate(self, plate_name: str, top_n: int = 5) -> List[PlateStockInfo]:
        """
        获取板块内涨幅最大的前N只股票
        Args:
            plate_name: 板块名称
            top_n: 返回前N只股票
        Returns:
            股票信息列表（按涨跌幅降序）
        """
        stocks_info = self.get_plate_stocks(plate_name)
        if not stocks_info:
            return []
        # 按涨跌幅降序排序
        stocks_info.sort(key=lambda x: x['change_pct'], reverse=True)
        return stocks_info[:top_n]


if __name__ == '__main__':
    print("=" * 80)
    print("板块动量分析系统")
    print("=" * 80)

    # 初始化服务
    service = PlateMomentumService()

    # 分析所有板块，获取前10强势板块
    print("\n[步骤 1] 分析所有板块动量...")
    top_plates = service.analyze_all_plates(top_n=10)

    # 显示结果
    print("\n" + "=" * 80)
    print("【TOP 10 强势板块】")
    print("=" * 80)
    print(f"{'排名':<6}{'板块名称':<20}{'动量得分':<12}{'平均涨幅':<12}{'上涨占比':<12}{'股票数':<8}")
    print("-" * 80)

    for idx, result in enumerate(top_plates, 1):
        print(f"{idx:<6}{result.plate_name:<20}{result.momentum_score:<12.4f}"
              f"{result.avg_change_pct:<12.2f}%{result.up_stock_ratio:<12.2f}%{result.total_stocks:<8}")

    # 分析第一强势板块的龙头股
    if top_plates:
        top_plate = top_plates[0]
        print(f"\n[步骤 2] 分析 [{top_plate.plate_name}] 板块龙头股...")

        top_stocks = service.get_top_stocks_in_plate(top_plate.plate_name, top_n=5)

        print("\n" + "=" * 80)
        print(f"【{top_plate.plate_name} - TOP 5 龙头股】")
        print("=" * 80)
        print(f"{'排名':<6}{'股票代码':<12}{'股票名称':<20}{'涨跌幅':<12}{'最新价':<12}")
        print("-" * 80)

        for idx, stock in enumerate(top_stocks, 1):
            print(f"{idx:<6}{stock['symbol']:<12}{stock['name']:<20}"
                  f"{stock['change_pct']:<12.2f}%{stock['close_price']:<12.2f}")

    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)
