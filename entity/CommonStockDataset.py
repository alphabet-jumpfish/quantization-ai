from datetime import datetime
from typing import TypedDict, List


# 股票代码', '时间', '开盘', '最高', '最低',
# '收盘', '涨幅', '振幅', '总手', '金额
class CommonStockDataset(TypedDict, total=False):
    """
    Common stock dataset
    :param period: 1, 5, 15, 30, 60 分钟的数据
    """
    symbol: str
    period: int
    max: str
    min: str
    open: str
    close: str
    datatime: datetime
