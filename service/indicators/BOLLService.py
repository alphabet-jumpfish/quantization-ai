from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.fetch.SystemFetchDataset import SystemFetchDataset


class BOLLDataPoint:
    """BOLL数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"BOLLDataPoint(time={self.datatime}, value={self.value:.4f})"


class BOLLService:
    """
    BOLL (Bollinger Bands) Indicators Service
    提供布林带指标的计算
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1, period: int = 20, std_dev: float = 2.0):
        """
        初始化BOLL指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
            period: 移动平均周期，默认20
            std_dev: 标准差倍数，默认2.0
        """
        self.time_interval = time_interval
        self.period = period
        self.std_dev = std_dev

    def _mid(self, dataset: List[CommonStockDataset]) -> List[BOLLDataPoint]:
        """
        计算BOLL中轨（移动平均线）
        MID = MA(CLOSE, period)
        Args:
            dataset: 股票数据集
        Returns:
            中轨数据点列表
        """
        if not dataset or len(dataset) < self.period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算移动平均线
        mid = df['close'].rolling(window=self.period, min_periods=1).mean()

        # 转换为BOLLDataPoint列表
        result = []
        for i in range(len(df)):
            mid_value = float(mid.iloc[i]) if pd.notna(mid.iloc[i]) else 0.0
            result.append(BOLLDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=mid_value
            ))

        return result

    def _upper(self, dataset: List[CommonStockDataset]) -> List[BOLLDataPoint]:
        """
        计算BOLL上轨
        UPPER = MID + std_dev * STD(CLOSE, period)
        Args:
            dataset: 股票数据集
        Returns:
            上轨数据点列表
        """
        if not dataset or len(dataset) < self.period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算移动平均线和标准差
        mid = df['close'].rolling(window=self.period, min_periods=1).mean()
        std = df['close'].rolling(window=self.period, min_periods=1).std()

        # 计算上轨
        upper = mid + self.std_dev * std

        # 转换为BOLLDataPoint列表
        result = []
        for i in range(len(df)):
            upper_value = float(upper.iloc[i]) if pd.notna(upper.iloc[i]) else 0.0
            result.append(BOLLDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=upper_value
            ))

        return result

    def _lower(self, dataset: List[CommonStockDataset]) -> List[BOLLDataPoint]:
        """
        计算BOLL下轨
        LOWER = MID - std_dev * STD(CLOSE, period)
        Args:
            dataset: 股票数据集
        Returns:
            下轨数据点列表
        """
        if not dataset or len(dataset) < self.period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算移动平均线和标准差
        mid = df['close'].rolling(window=self.period, min_periods=1).mean()
        std = df['close'].rolling(window=self.period, min_periods=1).std()

        # 计算下轨
        lower = mid - self.std_dev * std

        # 转换为BOLLDataPoint列表
        result = []
        for i in range(len(df)):
            lower_value = float(lower.iloc[i]) if pd.notna(lower.iloc[i]) else 0.0
            result.append(BOLLDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=lower_value
            ))

        return result


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化BOLL服务
    boll_service = BOLLService(time_interval=time_interval, period=20, std_dev=2.0)

    # 计算BOLL上轨、中轨、下轨
    upper_line = boll_service._upper(datasets)
    mid_line = boll_service._mid(datasets)
    lower_line = boll_service._lower(datasets)

    print(f"上轨总行数: {len(upper_line)}")
    print(f"中轨总行数: {len(mid_line)}")
    print(f"下轨总行数: {len(lower_line)}")

    print("\n上轨数据（前5行）:")
    for item in upper_line[:5]:
        print(item)

    print("\n中轨数据（前5行）:")
    for item in mid_line[:5]:
        print(item)

    print("\n下轨数据（前5行）:")
    for item in lower_line[:5]:
        print(item)
