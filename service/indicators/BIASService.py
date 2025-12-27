from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.fetch.SystemFetchDataset import SystemFetchDataset


class BIASDataPoint:
    """BIAS数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"BIASDataPoint(time={self.datatime}, value={self.value:.3f})"


class BIASService:
    """
    BIAS (Bias Ratio) Indicators Service
    提供乖离率指标的计算
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1,
                 period1: int = 6, period2: int = 12, period3: int = 24):
        """
        初始化BIAS指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
            period1: BIAS1周期，默认6
            period2: BIAS2周期，默认12
            period3: BIAS3周期，默认24
        """
        self.time_interval = time_interval
        self.period1 = period1
        self.period2 = period2
        self.period3 = period3

    def _calculate_bias(self, dataset: List[CommonStockDataset], period: int) -> List[BIASDataPoint]:
        """
        计算指定周期的BIAS指标
        BIAS = (收盘价 - N日移动平均价) / N日移动平均价 × 100
        Args:
            dataset: 股票数据集
            period: BIAS周期
        Returns:
            BIAS数据点列表
        """
        if not dataset or len(dataset) < period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算移动平均线
        ma = df['close'].rolling(window=period, min_periods=1).mean()

        # 计算BIAS
        bias = ((df['close'] - ma) / ma) * 100

        # 转换为BIASDataPoint列表
        result = []
        for i in range(len(df)):
            bias_value = float(bias.iloc[i]) if pd.notna(bias.iloc[i]) else 0.0
            result.append(BIASDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=bias_value
            ))

        return result

    def _bias(self, dataset: List[CommonStockDataset]) -> List[BIASDataPoint]:
        """
        计算BIAS1指标（6周期）
        Args:
            dataset: 股票数据集
        Returns:
            BIAS1数据点列表
        """
        return self._calculate_bias(dataset, period=self.period1)

    def _bias2(self, dataset: List[CommonStockDataset]) -> List[BIASDataPoint]:
        """
        计算BIAS2指标（12周期）
        Args:
            dataset: 股票数据集
        Returns:
            BIAS2数据点列表
        """
        return self._calculate_bias(dataset, period=self.period2)

    def _bias3(self, dataset: List[CommonStockDataset]) -> List[BIASDataPoint]:
        """
        计算BIAS3指标（24周期）
        Args:
            dataset: 股票数据集
        Returns:
            BIAS3数据点列表
        """
        return self._calculate_bias(dataset, period=self.period3)


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化BIAS服务
    bias_service = BIASService(time_interval=time_interval, period1=6, period2=12, period3=24)

    # 计算BIAS1、BIAS2、BIAS3线
    bias1_line = bias_service._bias(datasets)
    bias2_line = bias_service._bias2(datasets)
    bias3_line = bias_service._bias3(datasets)

    print(f"BIAS1线总行数: {len(bias1_line)}")
    print(f"BIAS2线总行数: {len(bias2_line)}")
    print(f"BIAS3线总行数: {len(bias3_line)}")

    print("\nBIAS1数据（前5行）:")
    for item in bias1_line[:5]:
        print(item)

    print("\nBIAS2数据（前5行）:")
    for item in bias2_line[:5]:
        print(item)

    print("\nBIAS3数据（前5行）:")
    for item in bias3_line[:5]:
        print(item)
