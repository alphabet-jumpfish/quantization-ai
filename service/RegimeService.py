from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

from service.indicators.DDService import DDService
from service.indicators.RSIService import RSIService
from service.indicators.BOLLService import BOLLService

from entity.CommonStockDataset import CommonStockDataset
from entity.TimeInterval import TimeInterval


class FactorResult:
    """因子计算结果"""

    def __init__(self, factor_name: str, datatime: datetime, value: float, weight: float = 1.0):
        self.factor_name = factor_name
        self.datatime = datatime
        self.value = value
        self.weight = weight

    def __repr__(self):
        return f"FactorResult(factor={self.factor_name}, time={self.datatime}, value={self.value:.4f}, weight={self.weight:.2f})"


class RegimeService:
    """
    多因子分析服务
    提供多因子计算、合成和评分的基础模板
    """

    def __init__(self, time_interval: TimeInterval = TimeInterval.MIN_1):
        """
        初始化多因子服务
        Args:
            time_interval: 时间间隔，用于标识数据源的时间分割
        """
        self.time_interval = time_interval
        self.factors = {}  # 存储因子权重配置

    def register_factor(self, factor_name: str, weight: float = 1.0):
        """
        注册因子及其权重
        Args:
            factor_name: 因子名称
            weight: 因子权重，默认1.0
        """
        self.factors[factor_name] = weight

    def calculate_macd(self, dataset: List[CommonStockDataset], period: int = 20) -> List[FactorResult]:
        """
        改进版MACD因子计算
        考虑：1. 金叉/死叉方向 2. MACD柱状图强度 3. 趋势持续时间
        """
        dd_service = DDService(time_interval=self.time_interval)
        dea_points = dd_service._dea(dataset)
        dif_points = dd_service._dif(dataset)
        macd_points = dd_service._macd(dataset)
        signal_points = dd_service.signal_line(dif_points=dif_points, dea_points=dea_points)

        result = []
        for i, signal_point in enumerate(signal_points):
            macd_custom_val = signal_point.value
            trend_direction = 0
            trend_duration = 0

            if macd_custom_val >= 200000:
                trend_direction = -1  # 空头
                trend_duration = macd_custom_val - 200000
            elif macd_custom_val >= 100000:
                trend_direction = 1  # 多头
                trend_duration = macd_custom_val - 100000

            # 改进1：加入MACD柱状图强度
            macd_strength = abs(macd_points[i].value) if i < len(macd_points) else 0.0

            # 改进2：趋势持续时间衰减（避免过度依赖持续时间）
            time_factor = min(trend_duration / period, 1.0)
            time_decay = 1.0 / (1.0 + 0.1 * trend_duration)  # 时间衰减因子

            # 改进3：综合得分 = 方向 × (时间因子 × 衰减 + 强度因子)
            # 强度归一化：假设MACD强度在0-10之间
            strength_factor = min(macd_strength / 10.0, 1.0)
            score = trend_direction * (0.5 * time_factor * time_decay + 0.5 * strength_factor)

            result.append(FactorResult(
                factor_name='macd',
                datatime=signal_point.datatime,
                value=score,
                weight=self.factors.get('macd', 1.0)
            ))

        return result

    def calculate_momentum_factor(self, dataset: List[CommonStockDataset], period: int = 20) -> List[FactorResult]:
        if not dataset or len(dataset) < period:
            return []
        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算动量
        momentum = df['close'].pct_change(periods=period) * 100

        result = []
        for i in range(len(df)):
            value = float(momentum.iloc[i]) if pd.notna(momentum.iloc[i]) else 0.0
            result.append(FactorResult(
                factor_name='momentum',
                datatime=df.iloc[i]['datatime'],
                value=value,
                weight=self.factors.get('momentum', 1.0)
            ))

        return result

    def calculate_rsi_factor(self, dataset: List[CommonStockDataset], period: int = 14) -> List[FactorResult]:
        """
        计算RSI因子
        RSI > 70: 超买，得分为负
        RSI < 30: 超卖，得分为正
        RSI = 50: 中性，得分为0
        """
        rsi_service = RSIService(time_interval=self.time_interval)
        rsi_points = rsi_service._calculate_rsi(dataset, period=period)

        result = []
        for rsi_point in rsi_points:
            rsi_value = rsi_point.value

            # RSI转换为[-1, 1]区间的得分
            if rsi_value >= 70:
                score = -1.0 * min((rsi_value - 70) / 30, 1.0)
            elif rsi_value <= 30:
                score = 1.0 * min((30 - rsi_value) / 30, 1.0)
            else:
                score = (50 - rsi_value) / 20.0

            result.append(FactorResult(
                factor_name='rsi',
                datatime=rsi_point.datatime,
                value=score,
                weight=self.factors.get('rsi', 1.0)
            ))

        return result

    def calculate_volatility_factor(self, dataset: List[CommonStockDataset], period: int = 20) -> List[FactorResult]:
        """
        计算波动率因子
        波动率越高，风险越大，得分越低
        """
        if not dataset or len(dataset) < period:
            return []

        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        # 计算收益率
        returns = df['close'].pct_change()

        # 计算滚动标准差（波动率）
        volatility = returns.rolling(window=period, min_periods=1).std() * 100

        # 计算波动率的均值和标准差用于标准化
        vol_mean = volatility.mean()
        vol_std = volatility.std()

        result = []
        for i in range(len(df)):
            vol_value = float(volatility.iloc[i]) if pd.notna(volatility.iloc[i]) else 0.0

            # 波动率标准化后取负（波动率高=风险高=得分低）
            if vol_std > 1e-8:
                score = -1.0 * (vol_value - vol_mean) / vol_std
                score = max(min(score, 1.0), -1.0)  # 限制在[-1, 1]
            else:
                score = 0.0

            result.append(FactorResult(
                factor_name='volatility',
                datatime=df.iloc[i]['datatime'],
                value=score,
                weight=self.factors.get('volatility', 1.0)
            ))

        return result

    def calculate_factor_correlation(self, factor_results_list: List[List[FactorResult]]) -> pd.DataFrame:
        """
        计算因子之间的相关性矩阵
        用于检测因子是否存在多重共线性
        Args:
            factor_results_list: 多个因子结果列表
        Returns:
            相关性矩阵DataFrame
        """
        if not factor_results_list or len(factor_results_list) < 2:
            return pd.DataFrame()

        # 构建因子值矩阵
        factor_dict = {}
        for factor_results in factor_results_list:
            if not factor_results:
                continue
            factor_name = factor_results[0].factor_name
            factor_dict[factor_name] = [fr.value for fr in factor_results]

        df = pd.DataFrame(factor_dict)
        correlation_matrix = df.corr()

        return correlation_matrix

    def combine_factors(self, factor_results_list: List[List[FactorResult]]) -> List[Dict]:
        """
        合成多个因子
        使用加权平均方法合成因子
        Args:
            factor_results_list: 多个因子结果列表
        Returns:
            合成后的因子字典列表
        """
        if not factor_results_list:
            return []

        # 将所有因子结果转换为DataFrame
        all_factors = []
        for factor_results in factor_results_list:
            for fr in factor_results:
                all_factors.append({
                    'datatime': fr.datatime,
                    'factor_name': fr.factor_name,
                    'value': fr.value,
                    'weight': fr.weight
                })

        df = pd.DataFrame(all_factors)

        # 对每个因子在整个时间序列上进行Z-score标准化
        for factor_name in df['factor_name'].unique():
            factor_mask = df['factor_name'] == factor_name
            factor_values = df.loc[factor_mask, 'value']

            # Z-score标准化：(x - mean) / std
            mean = factor_values.mean()
            std = factor_values.std()

            if std > 1e-8:  # 避免除以0
                df.loc[factor_mask, 'normalized_value'] = (factor_values - mean) / std
            else:
                df.loc[factor_mask, 'normalized_value'] = 0.0

        # 按时间分组，计算加权平均
        combined = []
        for datatime, group in df.groupby('datatime'):
            # 计算加权得分
            weighted_score = (group['normalized_value'] * group['weight']).sum() / group['weight'].sum()
            combined.append({
                'datatime': datatime,
                'composite_score': float(weighted_score),
                'factor_count': len(group)
            })

        return combined


if __name__ == '__main__':

    from service.SystemFetchDataset import SystemFetchDataset

    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")
    # 初始化多因子服务
    regime_service = RegimeService(time_interval=time_interval)
    # 注册因子及权重
    # 建议的因子组合
    regime_service.register_factor('macd', weight=2.0)  # 趋势
    regime_service.register_factor('volatility', weight=1.0)  # 波动率
    regime_service.register_factor('rsi', weight=1.5)  # 超买超卖
    regime_service.register_factor('momentum', weight=1.0)  # 动量

    # 计算各个因子
    macd_factors = regime_service.calculate_macd(datasets, period=20)
    rsi_factors = regime_service.calculate_rsi_factor(datasets, period=14)
    momentum_factors = regime_service.calculate_momentum_factor(datasets, period=20)
    volatility_factors = regime_service.calculate_volatility_factor(datasets, period=20)
    print(f"\n动量因子总行数: {len(momentum_factors)}")
    print(f"\nMACD因子总行数: {len(macd_factors)}")
    print(f"\nRSI因子总行数: {len(rsi_factors)}")
    print(f"\n波动率因子总行数: {len(volatility_factors)}")

    # 计算因子相关性
    print("\n=== 因子相关性分析 ===")
    correlation_matrix = regime_service.calculate_factor_correlation([
        macd_factors,
        rsi_factors,
        momentum_factors,
        volatility_factors
    ])
    print("\n因子相关性矩阵:")
    print(correlation_matrix)


    # 合成因子
    print("\n=== 合成因子 ===")
    combined_factors = regime_service.combine_factors([
        macd_factors,
        rsi_factors,
        momentum_factors,
        volatility_factors
    ])
    print(f"合成因子总行数: {len(combined_factors)}")

    # print(combined_factors)

    # 显示前5个合成因子结果
    print("\n合成因子数据（前5行）:")
    for item in combined_factors[:5]:
        print(f"时间: {item['datatime']}, 综合得分: {item['composite_score']:.4f}, 因子数量: {item['factor_count']}")

    for item in combined_factors:
        print(item)

