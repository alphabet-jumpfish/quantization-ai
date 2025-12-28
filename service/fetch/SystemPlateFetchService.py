from typing import List

import pandas
import numpy
import akshare

from entity.PlateDataset import PlateStockInfo


class SystemPlateFetchService:

    def __init__(self):
        pass

    # 获取所有行业板块列表
    def get_plate_list(self) -> pandas.DataFrame:
        """
        获取所有行业板块列表
        Returns:
            板块列表 DataFrame
        """
        try:
            plate_df = akshare.stock_board_industry_name_em()
            print(f"\n=== 获取板块列表成功 ===")
            print(f"板块总数: {len(plate_df)}")
            return plate_df
        except Exception as e:
            print(f"获取板块列表失败: {e}")
            return pandas.DataFrame()

    # 板块成分股
    def get_plate_stocks(self, plate_name: str) -> List[PlateStockInfo]:
        # 获取板块成分股
        stocks_df = akshare.stock_board_industry_cons_em(symbol=plate_name)
        stocks_info = []
        for _, row in stocks_df.iterrows():
            stock_info: PlateStockInfo = {
                'symbol': row['代码'],
                'name': row['名称'],
                'plate_name': plate_name,
                'close_price': float(row.get('最新价', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0))
            }
            stocks_info.append(stock_info)
        return stocks_info
