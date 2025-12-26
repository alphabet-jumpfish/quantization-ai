from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.SystemFetchDataset import SystemFetchDataset


class KDJDataPoint:
    """KDJ数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"KDJDataPoint(time={self.datatime}, value={self.value:.3f})"


class KDJService:
    """
    KDJ Indicators Service
    提供KDJ指标的计算
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1,
                 n: int = 9, m1: int = 3, m2: int = 3):
        """
        初始化KDJ指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
            n: RSV周期，默认9
            m1: K值平滑周期，默认3
            m2: D值平滑周期，默认3
        """
        self.time_interval = time_interval
        self.n = n
        self.m1 = m1
        self.m2 = m2

    def _k(self, dataset: List[CommonStockDataset]) -> List[KDJDataPoint]:
        """
        计算K值
        K = (2/3) × 前一日K值 + (1/3) × 当日RSV
        Args:
            dataset: 股票数据集
        Returns:
            K值数据点列表
        """
        if not dataset or len(dataset) < self.n:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        print(f"_k方法中 df长度: {len(df)}")

        df['close'] = df['close'].astype(float)
        df['max'] = df['max'].astype(float)
        df['min'] = df['min'].astype(float)

        # 计算RSV (未成熟随机值)
        low_list = df['min'].rolling(window=self.n, min_periods=self.n).min()
        high_list = df['max'].rolling(window=self.n, min_periods=self.n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100

        # 计算K值 (使用EMA平滑)
        k = rsv.ewm(alpha=1/self.m1, adjust=False).mean()

        # 转换为KDJDataPoint列表
        result = []
        for i in range(len(df)):
            # 保留所有行，NaN值用0替代
            k_value = float(k.iloc[i]) if pd.notna(k.iloc[i]) else 0.0
            result.append(KDJDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=k_value
            ))
        return result

    def _d(self, dataset: List[CommonStockDataset]) -> List[KDJDataPoint]:
        """
        计算D值
        D = (2/3) × 前一日D值 + (1/3) × 当日K值
        Args:
            dataset: 股票数据集
        Returns:
            D值数据点列表
        """
        if not dataset or len(dataset) < self.n:
            return []

        # 转换为DataFrame以获取完整的时间序列
        df = pd.DataFrame(dataset)

        # 先计算K值
        k_points = self._k(dataset)
        if not k_points:
            return []
        # 将K值转换为Series
        k_values = pd.Series([point.value for point in k_points])
        # 计算D值 (对K值进行EMA平滑)
        d = k_values.ewm(alpha=1/self.m2, adjust=False).mean()
        # 转换为KDJDataPoint列表，保持与原始数据相同的行数
        result = []
        for i in range(len(df)):
            d_value = float(d.iloc[i]) if i < len(d) and pd.notna(d.iloc[i]) else 0.0
            result.append(KDJDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=d_value
            ))
        return result

    def _j(self, dataset: List[CommonStockDataset]) -> List[KDJDataPoint]:
        """
        计算J值
        J = 3K - 2D
        Args:
            dataset: 股票数据集
        Returns:
            J值数据点列表
        """
        if not dataset or len(dataset) < self.n:
            return []

        # 计算K值和D值
        k_points = self._k(dataset)
        d_points = self._d(dataset)

        if not k_points or not d_points:
            return []

        # 计算J值，保持与原始数据相同的行数
        result = []
        for i in range(len(k_points)):
            j_value = 3 * k_points[i].value - 2 * d_points[i].value
            result.append(KDJDataPoint(
                datatime=k_points[i].datatime,
                value=float(j_value)
            ))

        return result


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化KDJ服务
    kdj_service = KDJService(time_interval=time_interval)

    # 计算K、D、J线
    k_line = kdj_service._k(datasets)
    d_line = kdj_service._d(datasets)
    j_line = kdj_service._j(datasets)

    print(f"K线总行数: {len(k_line)}")
    print(f"D线总行数: {len(d_line)}")
    print(f"J线总行数: {len(j_line)}")

    print("\nK线数据:")
    for item in k_line[:5]:
        print(item)

    print("\nD线数据:")
    for item in d_line[:5]:
        print(item)

    print("\nJ线数据:")
    for item in j_line[:5]:
        print(item)
