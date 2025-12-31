# vnpy_emt 安装成功指南

## 安装结果

✅ **vnpy_emt 已成功安装在 Python 3.10 环境中**

## 环境信息

- **Python 版本**: 3.10.19
- **Conda 环境名**: quantization-ai-py310
- **环境路径**: `C:\Users\wangjiawen\.conda\envs\quantization-ai-py310`

## 已安装的包

### 核心包
- ✅ vnpy_emt-2.10.0
- ✅ vnpy-4.3.0
- ✅ vnpy_ctastrategy-1.4.1

### 依赖包
- numpy-2.2.6
- pandas-2.3.3
- pyside6-6.8.2.1
- plotly-6.5.0
- pyqtgraph-0.14.0
- ta-lib-0.6.8
- 其他依赖...

## 关键发现

### 为什么 Python 3.12 失败？

**问题**: vnpy_emt 在 Python 3.12 和 3.11 上编译失败

**原因**:
- vnpy_emt 使用的 pybind11 版本过旧
- 与 Python 3.11+ 的 C API 不兼容
- 编译错误：`error C2027: 使用了未定义类型"_frame"`

**解决方案**:
- ✅ 使用 Python 3.10（有预编译的 wheel 文件）
- ❌ Python 3.11/3.12 需要等待官方更新

## 如何使用

### 激活环境

```bash
conda activate quantization-ai-py310
```

### 运行东方财富模拟盘服务

```bash
conda run -n quantization-ai-py310 python -m service.EMTPaperTradingService
```

### 验证安装

```bash
conda run -n quantization-ai-py310 python -c "import vnpy_emt; print('vnpy_emt installed successfully')"
```

## 下一步

### 1. 配置东方财富账号

在 `service/EMTPaperTradingService.py` 中修改账号密码：

```python
service.connect_emt_gateway(
    account="your_account",      # 替换为你的账号
    password="your_password"     # 替换为你的密码
)
```

### 2. 运行策略

策略已配置好 BOLL + CCI 双因子：
- BOLL 权重: 2.0 (57%)
- CCI 权重: 1.5 (43%)
- 止损: 3% | 止盈: 8% | 移动止损: 2%

### 3. 注意事项

⚠️ **重要提示**：
- 确保在交易时间段内运行（9:30-15:00）
- 首次运行建议小资金测试
- 关注日志输出，监控策略运行状态

## 常见问题

### Q: 如何切换回原来的 Python 3.12 环境？

```bash
conda activate quantization-ai
```

### Q: 两个环境可以共存吗？

可以。你现在有两个环境：
- `quantization-ai` (Python 3.12) - 用于回测
- `quantization-ai-py310` (Python 3.10) - 用于 vnpy_emt 实盘

### Q: 如何卸载 Python 3.10 环境？

```bash
conda env remove -n quantization-ai-py310
```

## 总结

✅ **成功完成**：
1. 创建 Python 3.10 环境
2. 安装 vnpy_emt 及所有依赖
3. 验证安装成功
4. 配置东方财富模拟盘服务

🎉 **现在可以开始使用东方财富模拟盘进行实盘测试了！**
