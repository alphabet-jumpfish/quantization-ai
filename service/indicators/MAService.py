from typing import List
from datetime import datetime
import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.fetch.SystemFetchDataset import SystemFetchDataset

class MADataPoint:
    """MA数据点，包含时间和值"""
    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"MADataPoint(time={self.datatime}, value={self.value:.2f})"


class MAService:
    """
    Moving Average (MA) Indicators Service
    提供各种移动平均线指标的计算
    """
    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1):
        """
        初始化MA指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
        """
        self.time_interval = time_interval


    def _calculate_ma_line(self, dataset: List[CommonStockDataset], period: int) -> List[MADataPoint]:
        """
        计算MA线（带时间戳的连续数据点）- 使用pandas rolling方法
        Args:
            dataset: 股票数据集
            period: MA周期
        Returns:
            List[MADataPoint]: MA数据点列表
        """
        if not dataset or len(dataset) < period:
            return []
        # 将数据转换为DataFrame
        df = pd.DataFrame([
            {
                'datatime': data['datatime'],
                'close': float(data['close'])
            }
            for data in dataset
        ])
        # 使用pandas rolling方法计算MA
        df['ma'] = df['close'].rolling(window=period, min_periods=period).mean()
        # 过滤掉NaN值并转换为MADataPoint列表
        ma_line = [
            MADataPoint(datatime=row['datatime'], value=row['ma'])
            for _, row in df.dropna(subset=['ma']).iterrows()
        ]
        return ma_line

    def _ma5_(self, dataset: List[CommonStockDataset]) -> List[MADataPoint]:
        return self._calculate_ma_line(dataset, period=5)

    def _ma10_(self, dataset: List[CommonStockDataset]) -> List[MADataPoint]:
        """Calculate 10-day Moving Average line / 计算10日移动平均线"""
        return self._calculate_ma_line(dataset, period=10)

    def _ma20_(self, dataset: List[CommonStockDataset]) -> List[MADataPoint]:
        """Calculate 20-day Moving Average line / 计算20日移动平均线"""
        return self._calculate_ma_line(dataset, period=20)

    def _ma30_(self, dataset: List[CommonStockDataset]) -> List[MADataPoint]:
        """Calculate 30-day Moving Average line / 计算30日移动平均线"""
        return self._calculate_ma_line(dataset, period=30)

    def _ma60_(self, dataset: List[CommonStockDataset]) -> List[MADataPoint]:
        """Calculate 60-day Moving Average line / 计算60日移动平均线"""
        return self._calculate_ma_line(dataset, period=60)


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))
    print(f"\n时间间隔: {time_interval.value}")
    # 初始化MA服务
    ma_service = MAService(time_interval=time_interval)
    # 计算MA5线
    ma5_line = ma_service._ma5_(datasets)
    print(f"\n=== MA5 计算结果（共 {len(ma5_line)} 个数据点）===")
    print(ma5_line)
