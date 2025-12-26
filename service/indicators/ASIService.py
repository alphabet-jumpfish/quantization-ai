from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.SystemFetchDataset import SystemFetchDataset


class ASIDataPoint:
    """ASI数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"ASIDataPoint(time={self.datatime}, value={self.value:.3f})"


class ASIService:
    """
    ASI (Accumulation Swing Index) Indicators Service
    提供振动升降指标的计算
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1, asit_period: int = 10):
        """
        初始化ASI指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
            asit_period: ASIT移动平均周期，默认10
        """
        self.time_interval = time_interval
        self.asit_period = asit_period

    def _asi(self, dataset: List[CommonStockDataset]) -> List[ASIDataPoint]:
        """
        计算ASI指标（振动升降指标）
        ASI是累积振动指标，用于判断趋势的真实性
        Args:
            dataset: 股票数据集
        Returns:
            ASI数据点列表
        """
        if not dataset or len(dataset) < 2:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['open'] = df['open'].astype(float)
        df['close'] = df['close'].astype(float)
        df['max'] = df['max'].astype(float)
        df['min'] = df['min'].astype(float)

        # 计算SI (Swing Index)
        si_values = []
        for i in range(len(df)):
            if i == 0:
                si_values.append(0.0)
                continue

            # 获取当前和前一日的数据
            close = df.iloc[i]['close']
            close_prev = df.iloc[i-1]['close']
            open_val = df.iloc[i]['open']
            high = df.iloc[i]['max']
            low = df.iloc[i]['min']
            high_prev = df.iloc[i-1]['max']
            low_prev = df.iloc[i-1]['min']

            # 计算A, B, C, D, E, R
            a = abs(high - close_prev)
            b = abs(low - close_prev)
            c = abs(high - low_prev)
            d = abs(close_prev - open_val)

            # 计算E (取A, B, C中的最大值)
            e = max(a, b, c)

            # 计算R
            if a >= b and a >= c:
                r = a - 0.5 * b + 0.25 * d
            elif b >= a and b >= c:
                r = b - 0.5 * a + 0.25 * d
            else:
                r = c + 0.25 * d

            # 计算K (通常取最大价格的1/10作为限制因子)
            k = max(a, b)

            # 计算SI
            if r != 0 and k != 0:
                si = 50 * ((close - close_prev) + 0.5 * (close - open_val) + 0.25 * (close_prev - df.iloc[i-1]['open'])) / r * k / e
            else:
                si = 0.0

            si_values.append(si)

        # 计算ASI (累积SI)
        asi_values = []
        cumulative_asi = 0.0
        for si in si_values:
            cumulative_asi += si
            asi_values.append(cumulative_asi)

        # 转换为ASIDataPoint列表
        result = []
        for i in range(len(df)):
            result.append(ASIDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=float(asi_values[i])
            ))

        return result

    def _asit(self, dataset: List[CommonStockDataset]) -> List[ASIDataPoint]:
        """
        计算ASIT指标（ASI的移动平均线）
        ASIT = MA(ASI, period)
        Args:
            dataset: 股票数据集
        Returns:
            ASIT数据点列表
        """
        if not dataset or len(dataset) < 2:
            return []

        # 先计算ASI
        asi_points = self._asi(dataset)
        if not asi_points:
            return []

        # 将ASI值转换为Series
        asi_values = pd.Series([point.value for point in asi_points])

        # 计算ASIT（ASI的移动平均）
        asit = asi_values.rolling(window=self.asit_period, min_periods=1).mean()

        # 转换为ASIDataPoint列表
        result = []
        for i in range(len(asi_points)):
            asit_value = float(asit.iloc[i]) if pd.notna(asit.iloc[i]) else 0.0
            result.append(ASIDataPoint(
                datatime=asi_points[i].datatime,
                value=asit_value
            ))

        return result


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化ASI服务
    asi_service = ASIService(time_interval=time_interval, asit_period=10)

    # 计算ASI和ASIT线
    asi_line = asi_service._asi(datasets)
    asit_line = asi_service._asit(datasets)

    print(f"ASI线总行数: {len(asi_line)}")
    print(f"ASIT线总行数: {len(asit_line)}")

    print("\nASI数据（前5行）:")
    for item in asi_line[:5]:
        print(item)

    print("\nASIT数据（前5行）:")
    for item in asit_line[:5]:
        print(item)
