"""回测验证框架

验证 AI 分析模型的预测准确率。
方案一: 用历史数据模拟过去决策, 与实际走势对比。

用法:
  python main.py backtest              # 单日期回测
  python main.py backtest:multi        # 多日期批量回测
"""
