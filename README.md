# Quantization AI - 多因子量化交易系统

基于 VeighNa 框架的 A 股多因子量化交易回测系统，支持技术指标计算、因子合成、策略回测等功能。

## 项目简介

本项目是一个完整的量化交易研究框架，专注于中国 A 股市场的多因子策略开发与回测。系统采用模块化设计，支持：

- 多数据源接入（AkShare、yfinance）
- 丰富的技术指标库（MACD、RSI、KDJ、BOLL、BIAS、ASI 等）
- 多因子合成与评分系统
- 基于 VeighNa 的专业回测引擎
- 完整的风险管理与绩效评估

## 项目结构

```
quantization-ai/
├── entity/                      # 数据实体定义
│   ├── CommonStockDataset.py   # 股票数据集结构
│   └── TimeInterval.py          # 时间间隔枚举
├── service/                     # 核心服务层
│   ├── indicators/              # 技术指标服务
│   │   ├── MAService.py         # 移动平均线
│   │   ├── DDService.py         # MACD指标
│   │   ├── RSIService.py        # RSI指标
│   │   ├── KDJService.py        # KDJ指标
│   │   ├── BOLLService.py       # 布林带
│   │   ├── BIASService.py       # 乖离率
│   │   └── ASIService.py        # 振动升降指标
│   ├── SystemFetchDataset.py   # 数据获取服务
│   ├── RegimeService.py         # 多因子分析服务
│   └── VeighNaBackTestService.py # VeighNa回测服务
├── test/                        # 测试目录
├── dataset/                     # 数据存储目录
├── requirements.txt             # 项目依赖
└── README.md                    # 项目文档
```

## 快速开始

### 环境要求

- Python >= 3.8
- pandas >= 2.2.3
- numpy >= 2.2.3
- vnpy >= 4.3.0

### 安装依赖

```bash
pip install -r requirements.txt
```

## 核心功能

### 1. 数据获取 (Data Acquisition)

**支持的数据源：**
- **AkShare**: 免费开源的 A 股数据接口，支持分钟级行情数据
- **yfinance**: 全球市场数据（美股、港股等）

**使用示例：**

```python
from service.fetch.SystemFetchDataset import SystemFetchDataset

fetch = SystemFetchDataset()
datasets = fetch._acquire_stock_dataset(
    symbol="000878",  # 股票代码
    start_str="20251225",  # 开始日期
    end_str="20251225",  # 结束日期
    period="1"  # 1分钟数据
)
```

**数据格式：**
- 支持 1/5/15/30/60 分钟级别数据
- 自动前复权处理
- 统一的数据结构 `CommonStockDataset`

### 2. 技术指标计算 (Technical Indicators)

系统内置 7 种常用技术指标服务：

| 指标 | 服务类 | 说明 | 文件位置 |
|------|--------|------|----------|
| MA | MAService | 移动平均线 | service/indicators/MAService.py |
| MACD | DDService | 指数平滑异同移动平均线 | service/indicators/DDService.py |
| RSI | RSIService | 相对强弱指标 | service/indicators/RSIService.py |
| KDJ | KDJService | 随机指标 | service/indicators/KDJService.py |
| BOLL | BOLLService | 布林带 | service/indicators/BOLLService.py |
| BIAS | BIASService | 乖离率 | service/indicators/BIASService.py |
| ASI | ASIService | 振动升降指标 | service/indicators/ASIService.py |

**特点：**
- 所有指标服务统一接口设计
- 支持自定义周期参数
- 返回标准化的指标数据结构

### 3. 多因子分析系统 (Multi-Factor Analysis)

**核心类：** `RegimeService` (service/RegimeService.py:27)

**支持的因子类型：**

#### 3.1 MACD 趋势因子
- 考虑金叉/死叉方向
- MACD 柱状图强度
- 趋势持续时间衰减
- 综合得分 = 方向 × (时间因子 × 衰减 + 强度因子)

#### 3.2 RSI 超买超卖因子
- RSI > 70: 超买（负分）
- RSI < 30: 超卖（正分）
- RSI = 50: 中性（0分）
- 得分范围：[-1, 1]

#### 3.3 动量因子 (Momentum)
- 基于价格变化率计算
- 可配置周期参数
- 反映价格趋势强度

#### 3.4 波动率因子 (Volatility)
- 滚动标准差计算
- Z-score 标准化
- 波动率越高，风险越大，得分越低

**因子合成方法：**
1. **Z-score 标准化**：对每个因子进行标准化处理
2. **加权平均**：根据因子权重计算综合得分
3. **相关性分析**：检测因子间的多重共线性

**使用示例：**
```python
from service.RegimeService import RegimeService
from entity.TimeInterval import TimeInterval

# 初始化多因子服务
time_interval = TimeInterval.from_period(1)
regime_service = RegimeService(time_interval=time_interval)

# 注册因子及权重
regime_service.register_factor('macd', weight=2.0)
regime_service.register_factor('rsi', weight=1.5)
regime_service.register_factor('momentum', weight=1.0)
regime_service.register_factor('volatility', weight=1.0)

# 计算各个因子
macd_factors = regime_service.calculate_macd(datasets, period=20)
rsi_factors = regime_service.calculate_rsi_factor(datasets, period=14)
momentum_factors = regime_service.calculate_momentum_factor(datasets, period=20)
volatility_factors = regime_service.calculate_volatility_factor(datasets, period=20)

# 合成因子
composite_scores = regime_service.combine_factors([
    macd_factors, rsi_factors, momentum_factors, volatility_factors
])
```

### 4. VeighNa 回测系统 (Backtesting)

**核心类：** `VeighNaBackTestService` (service/VeighNaBackTestService.py:91)

**回测流程：**

1. **配置回测参数**
2. **加载历史数据**
3. **计算多因子得分**
4. **运行回测引擎**
5. **分析回测结果**

**内置策略：** `MultiFactorStrategy` (service/VeighNaBackTestService.py:25)

**策略特点：**
- 基于多因子综合得分的买卖信号
- 支持止损/止盈设置
- 移动止损机制
- 固定仓位管理

**完整回测示例：**

```python
from datetime import datetime
from vnpy.trader.constant import Interval, Exchange
from service.VeighNaBackTestService import VeighNaBackTestService, MultiFactorStrategy
from service.fetch.SystemFetchDataset import SystemFetchDataset
from entity.TimeInterval import TimeInterval

# 1. 获取数据
fetch = SystemFetchDataset()
datasets = fetch._acquire_stock_dataset("000878", "20251225", "20251225", "1")

# 2. 初始化回测服务
backtest_service = VeighNaBackTestService()

# 3. 配置回测参数
backtest_service.setup_backtest(
    symbol="000878",
    exchange=Exchange.SSE,
    interval=Interval.MINUTE,
    start=datetime(2025, 12, 25, 9, 30),
    end=datetime(2025, 12, 25, 15, 0),
    rate=0.0003,  # 手续费率
    slippage=0.01,  # 滑点
    size=100,  # 合约乘数
    pricetick=0.01,  # 最小价格变动
    capital=100000  # 初始资金
)

# 4. 加载数据
bars = backtest_service.load_data(datasets, "000878", Exchange.SSE)

# 5. 计算多因子得分
time_interval = TimeInterval.from_period(1)
composite_scores = backtest_service.calculate_factors(datasets, time_interval)

# 6. 运行回测
strategy_setting = {
    "buy_threshold": 0.5,  # 买入阈值
    "sell_threshold": -0.5,  # 卖出阈值
    "fixed_size": 1,  # 固定手数
    "stop_loss_pct": 0.05,  # 止损比例 5%
    "take_profit_pct": 0.10  # 止盈比例 10%
}

result = backtest_service.run_backtest(bars, MultiFactorStrategy, strategy_setting)
print(result)
```

### 5. 绩效评估指标 (Performance Metrics)

回测系统提供完整的绩效评估指标：

**收益指标：**
- Total PnL: 总盈亏
- Net PnL: 净盈亏（扣除手续费）
- Total Return: 总收益率
- Annual Return: 年化收益率
- Daily Return: 日收益率

**交易统计：**
- Total Trades: 总交易次数
- Winning Trades: 盈利交易次数
- Losing Trades: 亏损交易次数
- Win Rate: 胜率

**盈亏分析：**
- Avg Winning Trade: 平均盈利
- Avg Losing Trade: 平均亏损
- Profit/Loss Ratio: 盈亏比

**风险指标：**
- Max Drawdown: 最大回撤金额
- Max Drawdown Percent: 最大回撤百分比
- Sharpe Ratio: 夏普比率（风险调整后收益）

## 快速运行

### 运行多因子分析示例

```bash
python service/RegimeService.py
```

### 运行完整回测示例

```bash
python service/VeighNaBackTestService.py
```

输出示例：
```
=== VeighNa Multi-Factor Backtest System ===

[OK] Data loaded: 240 bars

[Step 1] Configure Backtest
  - Symbol: 000878 | Capital: 100,000 CNY

[Step 2] Load Data
  - Loaded 240 bars

[Step 3] Calculate Factors
  - Scores: Min=-2.1234, Max=1.8765, Mean=0.0123

[Step 4] Run Backtest
  - Buy Threshold: 0.5000 | Sell Threshold: -0.5000

============================================================
[Backtest Results]
============================================================

>> Profit Metrics:
  Total PnL:           1234.56 CNY
  Net PnL:             1200.00 CNY
  Total Return:           1.20%
  Annual Return:         15.60%

>> Trade Statistics:
  Total Trades:              12
  Winning Trades:             8
  Losing Trades:              4
  Win Rate:               66.67%

>> Risk Metrics:
  Max Drawdown:           -2.50%
  Sharpe Ratio:             1.85
```

## 项目特色

### 1. 模块化设计
- 数据层、指标层、因子层、策略层分离
- 易于扩展和维护
- 支持自定义指标和因子

### 2. 专业回测引擎
- 基于 VeighNa 专业量化框架
- 支持分钟级高频回测
- 完整的滑点和手续费模拟

### 3. 多因子框架
- 支持多种因子类型
- 灵活的因子权重配置
- Z-score 标准化处理
- 因子相关性分析

### 4. 风险管理
- 止损/止盈机制
- 移动止损
- 仓位管理
- 最大回撤控制

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| 数据获取 | AkShare, yfinance | 免费开源的金融数据接口 |
| 数据处理 | pandas, numpy | 高性能数据分析库 |
| 回测框架 | VeighNa | 专业的量化交易框架 |
| 技术指标 | 自研指标库 | 7种常用技术指标 |
| 因子分析 | RegimeService | 多因子合成与评分系统 |

## 开发路线图

### 已完成 ✅
- [x] 数据获取模块（AkShare 集成）
- [x] 7种技术指标服务（MA, MACD, RSI, KDJ, BOLL, BIAS, ASI）
- [x] 多因子分析框架
- [x] VeighNa 回测引擎集成
- [x] 多因子策略实现
- [x] 完整的绩效评估系统

### 进行中 🚧
- [ ] 更多技术指标支持（ATR, CCI, OBV 等）
- [ ] 机器学习因子（基于 sklearn）
- [ ] 参数优化模块
- [ ] 可视化分析工具

### 计划中 📋
- [ ] 实盘交易接口
- [ ] Web 管理界面
- [ ] 策略组合管理
- [ ] 风险预警系统
- [ ] 数据库存储支持（ClickHouse/DolphinDB）

## 注意事项

### 风险提示
⚠️ **本项目仅供学习和研究使用，不构成任何投资建议。**

- 量化交易存在风险，历史回测结果不代表未来表现
- 实盘交易前请充分测试和验证策略
- 建议从小资金开始，逐步验证策略有效性
- 注意控制风险，设置合理的止损止盈

### 数据说明
- AkShare 数据免费但有访问频率限制
- 建议本地缓存历史数据，减少重复请求
- 数据质量直接影响回测结果，请注意数据清洗

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 如何贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循 PEP 8 Python 代码规范
- 添加必要的注释和文档字符串
- 编写单元测试
- 确保所有测试通过

## 参考资源

### 相关文档
- [VeighNa 官方文档](https://www.vnpy.com/)
- [AkShare 文档](https://akshare.akfamily.xyz/)
- [pandas 文档](https://pandas.pydata.org/)

### 推荐阅读
- 《量化交易：如何建立自己的算法交易》
- 《Python金融大数据分析》
- 《机器学习与量化投资》

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 致谢

感谢以下开源项目：

- [VeighNa](https://github.com/vnpy/vnpy) - 专业的量化交易框架
- [AkShare](https://github.com/akfamily/akshare) - 免费开源的金融数据接口
- [pandas](https://github.com/pandas-dev/pandas) - 强大的数据分析库

## 更新日志

### v1.0.0 (2025-12-26)
- ✨ 初始版本发布
- ✅ 完成数据获取模块
- ✅ 实现 7 种技术指标服务
- ✅ 完成多因子分析框架
- ✅ 集成 VeighNa 回测引擎
- ✅ 实现多因子策略
- ✅ 完整的绩效评估系统

---

**如果觉得这个项目对你有帮助，请给个 ⭐ Star 支持一下！**
