from datetime import datetime
from typing import List

import pandas as pd
from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval
from service.fetch.SystemFetchDataset import SystemFetchDataset


class CCIDataPoint:
    """CCI数据点，包含时间和值"""

    def __init__(self, datatime: datetime, value: float):
        self.datatime = datatime
        self.value = value

    def __repr__(self):
        return f"CCIDataPoint(time={self.datatime}, value={self.value:.3f})"


class CCIService:
    """
    CCI (Commodity Channel Index) Indicators Service
    提供CCI指标的计算
    CCI = (TP - MA) / (0.015 * MD)
    其中：
    TP = (最高价 + 最低价 + 收盘价) / 3
    MA = TP的N日简单移动平均
    MD = TP的N日平均绝对偏差
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1):
        """
        初始化CCI指标服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
        """
        self.time_interval = time_interval

    def _calculate_cci(self, dataset: List[CommonStockDataset], period: int) -> List[CCIDataPoint]:
        """
        计算指定周期的CCI指标
        Args:
            dataset: 股票数据集
            period: CCI周期
        Returns:
            CCI数据点列表
        """
        if not dataset or len(dataset) < period:
            return []

        # 转换为DataFrame
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)
        df['max'] = df['max'].astype(float)
        df['min'] = df['min'].astype(float)

        # 计算典型价格 TP = (High + Low + Close) / 3
        df['tp'] = (df['max'] + df['min'] + df['close']) / 3

        # 计算TP的N日简单移动平均 MA
        df['ma'] = df['tp'].rolling(window=period, min_periods=1).mean()

        # 计算平均绝对偏差 MD
        df['md'] = df['tp'].rolling(window=period, min_periods=1).apply(
            lambda x: (abs(x - x.mean())).mean(), raw=False
        )

        # 计算CCI = (TP - MA) / (0.015 * MD)
        result = []
        for i in range(len(df)):
            if pd.notna(df['ma'].iloc[i]) and pd.notna(df['md'].iloc[i]) and df['md'].iloc[i] != 0:
                cci_value = (df['tp'].iloc[i] - df['ma'].iloc[i]) / (0.015 * df['md'].iloc[i])
            else:
                cci_value = 0.0

            result.append(CCIDataPoint(
                datatime=df.iloc[i]['datatime'],
                value=float(cci_value)
            ))

        return result

    def _cci14(self, dataset: List[CommonStockDataset]) -> List[CCIDataPoint]:
        """
        计算CCI14指标（14周期）
        Args:
            dataset: 股票数据集
        Returns:
            CCI14数据点列表
        """
        return self._calculate_cci(dataset, period=14)

    def _cci20(self, dataset: List[CommonStockDataset]) -> List[CCIDataPoint]:
        """
        计算CCI20指标（20周期）
        Args:
            dataset: 股票数据集
        Returns:
            CCI20数据点列表
        """
        return self._calculate_cci(dataset, period=20)

    def _cci88(self, dataset: List[CommonStockDataset]) -> List[CCIDataPoint]:
        """
        计算CCI88指标（88周期）
        Args:
            dataset: 股票数据集
        Returns:
            CCI88数据点列表
        """
        return self._calculate_cci(dataset, period=88)


if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")

    # 初始化CCI服务
    cci_service = CCIService(time_interval=time_interval)

    # 计算CCI14、CCI20、CCI88线
    cci14_line = cci_service._cci14(datasets)
    cci20_line = cci_service._cci20(datasets)
    cci88_line = cci_service._cci88(datasets)

    print(f"CCI14线总行数: {len(cci14_line)}")
    print(f"CCI20线总行数: {len(cci20_line)}")
    print(f"CCI88线总行数: {len(cci88_line)}")

    print("\nCCI14数据（前5行）:")
    for item in cci14_line[:5]:
        print(item)

    print("\nCCI20数据（前5行）:")
    for item in cci20_line[:5]:
        print(item)

    print("\nCCI88数据（前5行）:")
    for item in cci88_line[:5]:
        print(item)
