from datetime import datetime
from typing import List
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from entity.CommonStockDataset import CommonStockDataset


class SystemConvertService:

    def __init__(self):
        pass

    def dataset_convert_bars(self, dataset: List[CommonStockDataset], symbol: str, exchange: Exchange):
        bars = []
        for data in dataset:
            dt = data['datatime']
            if isinstance(dt, str):
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')

            bar = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=dt,
                interval=Interval.MINUTE,
                volume=float(data.get('volume', 0)),
                open_price=float(data['open']),
                high_price=float(data['max']),
                low_price=float(data['min']),
                close_price=float(data['close']),
                gateway_name="BACKTEST"
            )
            bars.append(bar)
        return bars
