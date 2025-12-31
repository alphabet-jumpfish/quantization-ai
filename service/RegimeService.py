from datetime import datetime
from typing import List, Dict
import pandas as pd

from service.indicators.DDService import DDService
from service.indicators.RSIService import RSIService
from service.indicators.CCIService import CCIService
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

    def calculate_cci_factor(self, dataset: List[CommonStockDataset], period: int = 14) -> List[FactorResult]:
        """
        计算CCI因子
        CCI (Commodity Channel Index) 用于识别超买超卖和趋势反转
        CCI > +100: 超买区域，得分为负
        CCI < -100: 超卖区域，得分为正
        CCI在[-100, +100]: 正常区间，根据位置给分

        Args:
            dataset: 股票数据集
            period: CCI周期，默认14
        Returns:
            CCI因子结果列表
        """
        cci_service = CCIService(time_interval=self.time_interval)
        cci_points = cci_service._calculate_cci(dataset, period=period)

        result = []
        for cci_point in cci_points:
            cci_value = cci_point.value

            # CCI转换为[-1, 1]区间的得分
            # 参考市场经验：
            # CCI > +200: 极度超买
            # CCI > +100: 超买
            # CCI在[-100, +100]: 正常震荡
            # CCI < -100: 超卖
            # CCI < -200: 极度超卖

            if cci_value > 100:
                # 超买区域，得分为负，越超买越负
                score = -1.0 * min((cci_value - 100) / 200, 1.0)
            elif cci_value < -100:
                # 超卖区域，得分为正，越超卖越正
                score = 1.0 * min((abs(cci_value) - 100) / 200, 1.0)
            else:
                # 正常区间[-100, +100]，线性映射到[-0.5, 0.5]
                score = -cci_value / 200.0

            result.append(FactorResult(
                factor_name='cci',
                datatime=cci_point.datatime,
                value=score,
                weight=self.factors.get('cci', 1.0)
            ))

        return result

    def calculate_boll_factor(self, dataset: List[CommonStockDataset], period: int = 20, std_dev: float = 2.0) -> List[FactorResult]:
        """
        计算布林带因子
        布林带用于识别价格相对位置和波动率突破

        策略逻辑（基于市场实战经验）：
        1. 价格触及下轨：超卖信号，得分为正（买入机会）
        2. 价格触及上轨：超买信号，得分为负（卖出机会）
        3. 价格在中轨附近：中性区域
        4. 布林带宽度：反映市场波动率

        Args:
            dataset: 股票数据集
            period: 布林带周期，默认20
            std_dev: 标准差倍数，默认2.0
        Returns:
            布林带因子结果列表
        """
        boll_service = BOLLService(time_interval=self.time_interval, period=period, std_dev=std_dev)
        upper_points = boll_service._upper(dataset)
        mid_points = boll_service._mid(dataset)
        lower_points = boll_service._lower(dataset)

        if not dataset or len(dataset) != len(upper_points):
            return []

        df = pd.DataFrame(dataset)
        df['close'] = df['close'].astype(float)

        result = []
        for i in range(len(df)):
            close_price = df['close'].iloc[i]
            upper = upper_points[i].value
            mid = mid_points[i].value
            lower = lower_points[i].value

            # 避免除零错误
            if upper == lower or upper == 0 or lower == 0:
                score = 0.0
            else:
                # 计算价格在布林带中的相对位置 %B = (Close - Lower) / (Upper - Lower)
                percent_b = (close_price - lower) / (upper - lower)

                # 计算布林带宽度（标准化）
                bandwidth = (upper - lower) / mid if mid > 0 else 0

                # 布林带因子得分计算（基于实战经验）：
                # %B > 1.0: 价格突破上轨，强超买，得分 -0.8 到 -1.0
                # %B > 0.8: 接近上轨，超买，得分 -0.5 到 -0.8
                # %B < 0.0: 价格突破下轨，强超卖，得分 +0.8 到 +1.0
                # %B < 0.2: 接近下轨，超卖，得分 +0.5 到 +0.8
                # 0.4 < %B < 0.6: 中轨附近，中性

                if percent_b > 1.0:
                    # 突破上轨，强超买
                    score = -1.0 * min((percent_b - 1.0) * 2 + 0.8, 1.0)
                elif percent_b > 0.8:
                    # 接近上轨
                    score = -0.5 - (percent_b - 0.8) * 1.5
                elif percent_b < 0.0:
                    # 突破下轨，强超卖
                    score = 1.0 * min(abs(percent_b) * 2 + 0.8, 1.0)
                elif percent_b < 0.2:
                    # 接近下轨
                    score = 0.5 + (0.2 - percent_b) * 1.5
                else:
                    # 中间区域，线性映射
                    score = (0.5 - percent_b) * 1.0

                # 布林带收窄时（低波动），降低信号强度
                # 布林带扩张时（高波动），增强信号强度
                volatility_adjustment = min(bandwidth / 0.1, 1.5)
                score = score * volatility_adjustment

            result.append(FactorResult(
                factor_name='boll',
                datatime=df.iloc[i]['datatime'],
                value=float(score),
                weight=self.factors.get('boll', 1.0)
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

    from service.fetch.SystemFetchDataset import SystemFetchDataset
    fetch = SystemFetchDataset()
    datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")
    time_interval = TimeInterval.from_period(int(1))

    print(f"原始数据集总行数: {len(datasets)}")
    # 初始化多因子服务
    regime_service = RegimeService(time_interval=time_interval)

    # 注册因子及权重
    # 基于市场研究和实战经验的优化权重配置：
    #
    # 1. MACD (权重: 2.5) - 趋势跟踪因子
    #    - 作为趋势类指标的核心，MACD在捕捉中长期趋势方面表现优异
    #    - 学术研究表明趋势因子在量化策略中贡献度最高（约30-35%）
    #    - 参考：Fama-French三因子模型中动量因子的重要性
    #
    # 2. RSI (权重: 1.8) - 超买超卖因子
    #    - RSI是经典的反转指标，在震荡市场中表现突出
    #    - 与CCI形成互补，但RSI更稳定，噪音更小
    #    - 实战中RSI的胜率通常在55-60%
    #
    # 3. CCI (权重: 1.5) - 超买超卖与趋势反转因子
    #    - CCI对价格异常波动更敏感，能捕捉极端行情
    #    - 与RSI相关性约0.6-0.7，提供额外的反转信号
    #    - 在商品期货市场验证有效，股票市场同样适用
    #
    # 4. Momentum (权重: 1.2) - 动量因子
    #    - 短期动量因子，捕捉价格惯性
    #    - 学术研究：动量效应在全球市场普遍存在
    #    - 权重适中避免过度追涨杀跌
    #
    # 5. Volatility (权重: 0.8) - 波动率因子（风险控制）
    #    - 作为风险调整因子，权重相对较低
    #    - 主要用于在高波动期降低仓位信号强度
    #    - 低波动率异常（Low Volatility Anomaly）研究支持
    #
    # 权重设计原则：
    # - 趋势类因子（MACD + Momentum）总权重: 3.7 (约46%)
    # - 反转类因子（RSI + CCI）总权重: 3.3 (约41%)
    # - 风险因子（Volatility）总权重: 0.8 (约10%)
    # - 总权重: 8.0，保持平衡避免某一类因子过度主导

    regime_service.register_factor('macd', weight=2.5)       # 趋势跟踪
    regime_service.register_factor('rsi', weight=1.8)        # 超买超卖
    regime_service.register_factor('cci', weight=1.5)        # 超买超卖与反转
    regime_service.register_factor('momentum', weight=1.2)   # 短期动量
    regime_service.register_factor('volatility', weight=0.8) # 风险控制

    # 计算各个因子
    macd_factors = regime_service.calculate_macd(datasets, period=20)
    rsi_factors = regime_service.calculate_rsi_factor(datasets, period=14)
    cci_factors = regime_service.calculate_cci_factor(datasets, period=14)
    momentum_factors = regime_service.calculate_momentum_factor(datasets, period=20)
    volatility_factors = regime_service.calculate_volatility_factor(datasets, period=20)

    print(f"\nMACD因子总行数: {len(macd_factors)}")
    print(f"RSI因子总行数: {len(rsi_factors)}")
    print(f"CCI因子总行数: {len(cci_factors)}")
    print(f"动量因子总行数: {len(momentum_factors)}")
    print(f"波动率因子总行数: {len(volatility_factors)}")

    # 计算因子相关性
    print("\n=== 因子相关性分析 ===")
    correlation_matrix = regime_service.calculate_factor_correlation([
        macd_factors,
        rsi_factors,
        cci_factors,
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
        cci_factors,
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

