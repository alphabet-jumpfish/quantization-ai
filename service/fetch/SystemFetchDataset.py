import akshare
from entity.CommonStockDataset import CommonStockDataset


class SystemFetchDataset:

    def __init__(self):
        pass

    def _acquire_stock_dataset(self, symbol: str, start_str: str, end_str: str, period: str = "1"):
        df = akshare.stock_zh_a_hist_min_em(
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
            period=period,
            adjust="qfq"
        )
        print("\n=== 数据获取成功 ===")
        print(df.columns)
        print(f"总行数: {len(df)}")
        # 转换为 CommonStockDataset 列表
        datasets = []
        for index, row in df.iterrows():
            dataset: CommonStockDataset = {
                'symbol': symbol,
                'period': int(period),
                'max': str(row['最高']),
                'min': str(row['最低']),
                'open': str(row['开盘']),
                'close': str(row['收盘']),
                'datatime': row['时间']
            }
            datasets.append(dataset)
        datasets = sorted(datasets, key=lambda x: x['datatime'])
        print(f"\n前20条数据（按时间升序）:")
        for i, d in enumerate(datasets[:20]):
            print(f"{i + 1}. {d['datatime']} - Close: {d['close']}")

        return datasets



if __name__ == '__main__':
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
