"""
Time interval enumeration for stock data
"""
from enum import Enum


class TimeInterval(Enum):
    """
    时间间隔枚举
    Time interval enumeration for stock data analysis
    """
    # 分钟级别
    MIN_1 = "1min"      # 1分钟
    MIN_5 = "5min"      # 5分钟
    MIN_15 = "15min"    # 15分钟
    MIN_30 = "30min"    # 30分钟
    MIN_60 = "60min"    # 60分钟

    # 日级别
    DAY_1 = "1day"      # 1日
    DAY_2 = "2day"      # 2日
    DAY_3 = "3day"      # 3日
    DAY_5 = "5day"      # 5日
    DAY_10 = "10day"    # 10日

    # 周月季年
    WEEK = "week"       # 周
    MONTH = "month"     # 月
    QUARTER = "quarter" # 季
    YEAR = "year"       # 年

    @classmethod
    def from_period(cls, period: int) -> 'TimeInterval':
        """
        根据周期数字转换为时间间隔
        Convert period number to TimeInterval
        """
        mapping = {
            1: cls.MIN_1,
            5: cls.MIN_5,
            15: cls.MIN_15,
            30: cls.MIN_30,
            60: cls.MIN_60
        }
        return mapping.get(period, cls.MIN_1)
