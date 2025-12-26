from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.SystemFetchDataset import SystemFetchDataset


class DDDataPoint:
    """MA数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"DDDataPoint(time={self.datatime}, value={self.value:.3f})"


class DDService:
    """
    MACD (DIF/DEA) Indicators Service
    提供MACD指标的计算，包括DIF和DEA
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1,
                 fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        初始化MACD指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
            fast_period: 快速EMA周期，默认12
            slow_period: 慢速EMA周期，默认26
            signal_period: DEA信号线周期，默认9
        """
        self.time_interval = time_interval
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def _macd(self, dataset: List[CommonStockDataset]) -> List[DDDataPoint]:
        """
        计算MACD柱状图
        MACD = (DIF - DEA)*2
        Args:
            dataset: 股票数据集
        Returns:
            MACD数据点列表
        """
        if not dataset or len(dataset) < self.slow_period + self.signal_period:
            return []
        # 计算DIF和DEA
        dif_points = self._dif(dataset)
        dea_points = self._dea(dataset)
        if not dif_points or not dea_points:
            return []
        # 计算MACD柱状图
        result = []
        for i in range(len(dif_points)):
            macd_value = (dif_points[i].value - dea_points[i].value) * 2
            result.append(DDDataPoint(
                datatime=dif_points[i].datatime,
                value=float(macd_value)
            ))

        return result

    def _dif(self, dataset: List[CommonStockDataset]) -> List[DDDataPoint]:
        """
        计算DIF线（差离值）
        DIF = 快速EMA - 慢速EMA
        Args:
            dataset: 股票数据集
        Returns:
            DIF数据点列表
        """
        if not dataset or len(dataset) < self.slow_period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算快速和慢速EMA
        fast_ema = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = df['close'].ewm(span=self.slow_period, adjust=False).mean()

        # 计算DIF
        dif = fast_ema - slow_ema

        # 转换为DDDataPoint列表
        result = []
        for i in range(len(df)):
            result.append(DDDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=float(dif.iloc[i])
            ))

        return result

    def _dea(self, dataset: List[CommonStockDataset]) -> List[DDDataPoint]:
        """
        计算DEA线（信号线）
        DEA = DIF的EMA
        Args:
            dataset: 股票数据集
        Returns:
            DEA数据点列表
        """
        if not dataset or len(dataset) < self.slow_period + self.signal_period:
            return []

        # 先计算DIF
        dif_points = self._dif(dataset)
        if not dif_points:
            return []

        # 将DIF值转换为Series
        dif_values = pd.Series([point.value for point in dif_points])

        # 计算DEA（DIF的EMA）
        dea = dif_values.ewm(span=self.signal_period, adjust=False).mean()

        # 转换为DDDataPoint列表
        result = []
        for i in range(len(dif_points)):
            result.append(DDDataPoint(
                datatime=dif_points[i].datatime,
                value=float(dea.iloc[i])
            ))

        return result

    def signal_line(self, dif_points: List[DDDataPoint], dea_points: List[DDDataPoint]) -> List[DDDataPoint]:
        """
        通过DIF和DEA判断金叉和死叉信号
        金叉：DIF上穿DEA，信号从100000开始递增（100000, 100001, 100002...）
        死叉：DIF下穿DEA，信号从200000开始递增（200000, 200001, 200002...）
        Args:
            dataset: 股票数据集
        Returns:
            信号线数据点列表
        """

        # 计算DIF和DEA
        dif_points = dif_points
        dea_points = dea_points

        if not dif_points or not dea_points:
            return []

        result = []
        current_signal = 0  # 当前信号值
        signal_type = None  # 'golden' 或 'death'
        signal_counter = 0  # 信号计数器

        for i in range(len(dif_points)):
            dif_value = dif_points[i].value
            dea_value = dea_points[i].value

            # 判断金叉和死叉
            if i > 0:
                prev_dif = dif_points[i - 1].value
                prev_dea = dea_points[i - 1].value

                # 金叉：DIF从下方上穿DEA
                if prev_dif <= prev_dea and dif_value > dea_value:
                    signal_type = 'golden'
                    signal_counter = 0
                    current_signal = 100000

                # 死叉：DIF从上方下穿DEA
                elif prev_dif >= prev_dea and dif_value < dea_value:
                    signal_type = 'death'
                    signal_counter = 0
                    current_signal = 200000

                # 持续金叉或死叉状态
                elif signal_type == 'golden' and dif_value > dea_value:
                    signal_counter += 1
                    current_signal = 100000 + signal_counter

                elif signal_type == 'death' and dif_value < dea_value:
                    signal_counter += 1
                    current_signal = 200000 + signal_counter

            result.append(DDDataPoint(
                datatime=dif_points[i].datatime,
                value=float(current_signal)
            ))

        return result


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251226", "20251226", "1")
    time_interval = TimeInterval.from_period(int(1))

    # 初始化MACD服务
    dd_service = DDService(time_interval=time_interval)

    # 计算DIF、DEA、MACD和信号线
    dif_line = dd_service._dif(datasets)
    dea_line = dd_service._dea(datasets)
    macd_line = dd_service._macd(datasets)
    signal = dd_service.signal_line(dif_line, dea_line)

    print(f"DIF总行数: {len(dif_line)}")
    print(f"DEA总行数: {len(dea_line)}")
    print(f"MACD总行数: {len(macd_line)}")
    print(f"信号线总行数: {len(signal)}")

    for i in signal:
        print(i)

    # 查找金叉和死叉信号点
    print("\n=== 金叉信号点分析 ===")
    golden_crosses = [s for s in signal if 100000 <= s.value < 200000]
    if golden_crosses:
        print(f"金叉开始信号: {golden_crosses[0]}")
        if len(golden_crosses) > 1:
            print(f"金叉持续信号: {golden_crosses[1]}")
        if len(golden_crosses) > 2:
            print(f"金叉持续信号: {golden_crosses[2]}")
        print(f"金叉信号总数: {len(golden_crosses)}")
    else:
        print("未发现金叉信号")

    print("\n=== 死叉信号点分析 ===")
    death_crosses = [s for s in signal if s.value >= 200000]
    if death_crosses:
        print(f"死叉开始信号: {death_crosses[0]}")
        if len(death_crosses) > 1:
            print(f"死叉持续信号: {death_crosses[1]}")
        if len(death_crosses) > 2:
            print(f"死叉持续信号: {death_crosses[2]}")
        print(f"死叉信号总数: {len(death_crosses)}")
    else:
        print("未发现死叉信号")
