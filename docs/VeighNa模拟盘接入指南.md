# VeighNa 模拟盘接入指南

## 同花顺模拟盘说明

**重要提示**：VeighNa目前**不支持**直接接入同花顺模拟盘交易接口。

同花顺仅通过 `vnpy_ifind` 模块提供数据服务（需付费），不提供交易接口。

---

## 替代方案

### 方案1：东方财富模拟盘（推荐 - 免费）

**优点**：
- 完全免费
- 真实模拟交易环境
- 支持A股、港股、美股
- 数据实时更新

**接入步骤**：

#### 1. 注册模拟账号
访问东方财富官网注册模拟交易账号：
- 官网：https://www.18.cn/
- 注册后获取账号和密码

#### 2. 安装vnpy_emt模块
```bash
pip install vnpy_emt
```

#### 3. 使用示例代码
参考项目中的 `service/EMTPaperTradingService.py` 文件

```python
from service.EMTPaperTradingService import EMTPaperTradingService

# 创建服务
service = EMTPaperTradingService()
service.init_engines()

# 连接模拟盘
service.connect_emt_gateway(
    account="your_account",
    password="your_password"
)
```

---

### 方案2：华泰证券模拟盘

**优点**：
- 免费
- 接口稳定
- 支持股票、期权

**接入步骤**：

#### 1. 开通华泰证券账户
需要先开通华泰证券真实账户，然后申请模拟盘权限

#### 2. 安装vnpy_sec模块
```bash
pip install vnpy_sec
```

#### 3. 配置连接
```python
from vnpy_sec import SecGateway

setting = {
    "账号": "your_account",
    "密码": "your_password",
    "营业部代码": "your_branch_code",
    "通讯密码": "your_comm_password",
    "交易服务器": "模拟服务器地址",
}
```

---

### 方案3：期货SimNow模拟盘

**优点**：
- 完全免费
- 7x24小时运行
- 数据真实可靠
- 无需实名认证

**缺点**：
- 仅支持期货品种
- 不支持股票交易

**接入步骤**：

#### 1. 注册SimNow账号
访问：http://www.simnow.com.cn/
注册并获取账号密码

#### 2. 安装vnpy_ctp模块
```bash
pip install vnpy_ctp
```

#### 3. 配置连接
```python
from vnpy_ctp import CtpGateway

setting = {
    "用户名": "your_simnow_account",
    "密码": "your_password",
    "经纪商代码": "9999",
    "交易服务器": "180.168.146.187:10130",
    "行情服务器": "180.168.146.187:10131",
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000"
}
```

---

### 方案4：同花顺iFinD数据 + 本地模拟盘

**优点**：
- 数据质量高
- 完全本地控制
- 可自定义交易规则

**缺点**：
- 需要购买iFinD数据服务（付费）
- 无法测试真实交易环境

**接入步骤**：

#### 1. 购买iFinD数据服务
联系同花顺购买iFinDPy数据服务

#### 2. 安装vnpy_ifind模块
```bash
pip install vnpy_ifind
```

#### 3. 使用本地模拟账户
```python
from vnpy.gateway.paper import PaperGateway

# 配置纸面交易
paper_setting = {
    "行情网关": "IFIND",
    "资金": 1000000,
    "滑点": 0,
}
```

---

## 推荐方案对比

| 方案 | 费用 | 适用场景 | 推荐指数 |
|------|------|----------|----------|
| 东方财富模拟盘 | 免费 | 股票策略测试 | ⭐⭐⭐⭐⭐ |
| 华泰证券模拟盘 | 免费 | 股票、期权策略 | ⭐⭐⭐⭐ |
| 期货SimNow | 免费 | 期货策略测试 | ⭐⭐⭐⭐⭐ |
| 同花顺iFinD | 付费 | 专业量化研究 | ⭐⭐⭐ |

---

## 常见问题

### Q1: 为什么同花顺不能直接接入？
A: 同花顺主要提供数据服务，没有开放模拟交易接口给第三方平台。

### Q2: 哪个方案最适合股票策略？
A: 推荐使用东方财富模拟盘，免费且功能完善。

### Q3: 模拟盘和实盘有什么区别？
A: 主要区别在于：
- 模拟盘无真实资金风险
- 模拟盘可能存在滑点差异
- 模拟盘成交速度可能更快

### Q4: 如何从模拟盘切换到实盘？
A: 只需修改网关配置，将模拟服务器地址改为实盘服务器地址即可。

---

## 技术支持

如有问题，请参考：
- VeighNa官方文档：https://www.vnpy.com/docs/
- VeighNa GitHub：https://github.com/vnpy/vnpy
