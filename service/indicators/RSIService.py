from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.SystemFetchDataset import SystemFetchDataset


class RSIDataPoint:
    """RSI数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"RSIDataPoint(time={self.datatime}, value={self.value:.3f})"


class RSIService:
    """
    RSI (Relative Strength Index) Indicators Service
    提供RSI指标的计算
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1):
        """
        初始化RSI指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
        """
        self.time_interval = time_interval

    def _calculate_rsi(self, dataset: List[CommonStockDataset], period: int) -> List[RSIDataPoint]:
        """
        计算指定周期的RSI指标
        RSI = 100 - (100 / (1 + RS))
        其中 RS = 平均涨幅 / 平均跌幅
        Args:
            dataset: 股票数据集
            period: RSI周期
        Returns:
            RSI数据点列表
        """
        if not dataset or len(dataset) < period + 1:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算价格变动
        price_change = df['close'].diff()

        # 分离涨幅和跌幅
        gains = price_change.apply(lambda x: x if x > 0 else 0)
        losses = price_change.apply(lambda x: abs(x) if x < 0 else 0)

        # 计算平均涨幅和平均跌幅（使用EMA）
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()

        # 计算RSI
        result = []
        for i in range(len(df)):
            if pd.notna(avg_gains.iloc[i]) and pd.notna(avg_losses.iloc[i]):
                if avg_losses.iloc[i] == 0:
                    rsi_value = 100.0
                else:
                    rs = avg_gains.iloc[i] / avg_losses.iloc[i]
                    rsi_value = 100 - (100 / (1 + rs))
            else:
                rsi_value = 0.0

            result.append(RSIDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=float(rsi_value)
            ))

        return result

    def _rsi12(self, dataset: List[CommonStockDataset]) -> List[RSIDataPoint]:
        """
        计算RSI12指标（12周期）
        Args:
            dataset: 股票数据集
        Returns:
            RSI12数据点列表
        """
        return self._calculate_rsi(dataset, period=12)

    def _rsi16(self, dataset: List[CommonStockDataset]) -> List[RSIDataPoint]:
        """
        计算RSI16指标（16周期）
        Args:
            dataset: 股票数据集
        Returns:
            RSI16数据点列表
        """
        return self._calculate_rsi(dataset, period=16)

    def _rsi24(self, dataset: List[CommonStockDataset]) -> List[RSIDataPoint]:
        """
        计算RSI24指标（24周期）
        Args:
            dataset: 股票数据集
        Returns:
            RSI24数据点列表
        """
        return self._calculate_rsi(dataset, period=24)


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化RSI服务
    rsi_service = RSIService(time_interval=time_interval)

    # 计算RSI12、RSI16、RSI24线
    rsi12_line = rsi_service._rsi12(datasets)
    rsi16_line = rsi_service._rsi16(datasets)
    rsi24_line = rsi_service._rsi24(datasets)

    print(f"RSI12线总行数: {len(rsi12_line)}")
    print(f"RSI16线总行数: {len(rsi16_line)}")
    print(f"RSI24线总行数: {len(rsi24_line)}")

    print("\nRSI12数据（前5行）:")
    for item in rsi12_line[:5]:
        print(item)

    print("\nRSI16数据（前5行）:")
    for item in rsi16_line[:5]:
        print(item)

    print("\nRSI24数据（前5行）:")
    for item in rsi24_line[:5]:
        print(item)
