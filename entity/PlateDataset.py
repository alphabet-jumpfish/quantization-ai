from datetime import datetime
from typing import TypedDict, List


class PlateDataset(TypedDict, total=False):
    """
    板块数据集
    """
    plate_name: str  # 板块名称
    plate_code: str  # 板块代码
    stocks: List[str]  # 板块内股票列表
    datatime: datetime  # 数据时间


class PlateStockInfo(TypedDict, total=False):
    """
    板块成分股信息
    """
    symbol: str  # 股票代码
    name: str  # 股票名称
    plate_name: str  # 所属板块
    close_price: float  # 收盘价
    change_pct: float  # 涨跌幅
    volume: float  # 成交量
    amount: float  # 成交额
