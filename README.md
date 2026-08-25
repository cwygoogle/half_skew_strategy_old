# Half-Skew Strategy

本项目以中证 1000 股指期权（MO）和股指期货（IM）为研究对象，构建并回测固定期限 Half-Skew 策略。主要内容包括数据清洗、远期价格构造、隐含波动率拟合、风险暴露优化、Delta 对冲、资金占用计算以及 PnL 归因。

## 研究方法

### 1. 波动率曲线

对每个交易日和到期日，使用 Black–76 模型从 OTM 期权市场价格反解隐含波动率。定义

\[
k=\ln(K/F),
\]

并用二次函数拟合隐含波动率曲线：

\[
\sigma(k)=a+bk+\frac{1}{2}ck^2.
\]

其中，\(K\) 为执行价，\(F\) 为对应期限的远期价格。

### 2. Half-Skew定义

给定 log-moneyness 锚点 \(h\)，定义：

\[
\begin{aligned}
\mathrm{CallSkew}&=\sigma(h)-\sigma(0),\\
\mathrm{PutSkew}&=\sigma(-h)-\sigma(0),\\
\mathrm{WingCurvature}&=\frac{\mathrm{CallSkew}+\mathrm{PutSkew}}{2}.
\end{aligned}
\]

当前设置为 \(h=0.1\)。该参数表示在远期价格两侧选取 \(k=\pm0.1\) 作为 Skew 测量锚点。

### 3. 组合构建

策略按到期月份分别回测。每日从满足流动性、剩余期限、价格和 log-moneyness 条件的期权中选择候选合约，并求解带边界的最小二乘问题，使组合风险暴露满足：

\[
\begin{aligned}
\Gamma_{\mathrm{portfolio}}&\approx0,\\
\frac{\partial V_{\mathrm{portfolio}}}{\partial\sigma_{\mathrm{ATM}}}&\approx0,\\
\frac{\partial V_{\mathrm{portfolio}}}{\partial\mathrm{CallSkew}}
&\approx\mathrm{TargetCallSkew},\\
\frac{\partial V_{\mathrm{portfolio}}}{\partial\mathrm{PutSkew}}
&\approx\mathrm{TargetPutSkew}.
\end{aligned}
\]

优化目标包含 L2 仓位正则和资金占用惩罚，以降低风险矩阵病态时产生极端仓位的可能性，并抑制保证金或权利金占用较高的组合。期权仓位确定后，使用相同期限的 IM 期货对冲组合 Delta。

各项风险暴露为软目标。由于期权和期货仓位取整数，并受到仓位上限和单日交易上限约束，实际暴露允许在目标附近存在一定偏差。

### 4. PnL归因

项目使用模型全重估和 Taylor 展开分析组合收益，主要归因项包括：

- Delta PnL；
- Gamma PnL；
- ATM Vol PnL；
- Call Skew PnL；
- Put Skew PnL；
- Theta PnL；
- ATM Vol Vanna PnL；
- ATM Vol Volga PnL；
- Market Noise。

Market Noise 表示期权市场价格相对拟合模型价格的残差变化所产生的 PnL。手续费后实际收益为：

\[
\mathrm{ActualPnL}
=\mathrm{MarketPnL}-\mathrm{OptionFee}-\mathrm{FuturesFee}.
\]

回测结束时，对剩余仓位计提最终平仓手续费。

### 5. 资金占用与收益率

资金占用由期权权利金、期权保证金和期货保证金构成。最大占资收益率定义为：

\[
R_{\max}
=\frac{\text{累计手续费后PnL}}{\text{回测期间最大资金占用}}.
\]

若回测持有自然日数为 \(D\)，年化收益率为：

\[
R_{\mathrm{annual}}=(1+R_{\max})^{365/D}-1.
\]

## 项目结构

```text
.
├── 00_config.ipynb            # 全局参数
├── 01_data_processing.ipynb   # 数据读取与标准化
├── 02_basic_functions.ipynb   # Black–76定价、Greeks与基础函数
├── 03_repo_forward.ipynb      # 隐含Repo与Forward构造
├── 04_volatility_model.ipynb  # IV反解与二次波动率曲线拟合
├── 05_skew_curvature.ipynb    # Half-Skew期限结构
├── 06_skew_strategy.ipynb     # 策略回测、占资与PnL归因
├── run_all.ipynb              # 完整运行入口
├── 数据/                       # 原始行情数据
└── outputs/                    # 回测表格与图片
```

## 运行环境

项目使用 Python 和 Jupyter Notebook，主要依赖：

```bash
pip install jupyter numpy pandas scipy matplotlib
```

## 运行方式

在项目根目录打开 `run_all.ipynb`，选择已安装上述依赖的 Python 内核，然后从上到下运行全部单元格。

实际执行顺序为：

```text
00_config
02_basic_functions
01_data_processing
03_repo_forward
04_volatility_model
05_skew_curvature
06_skew_strategy
```

原始数据默认位于：

```text
数据/标的_2026-06~07.csv
数据/MO_2026-06~07.csv
```

## 主要参数

参数统一在 `00_config.ipynb` 中设置。当前策略的核心参数如下：

| 参数 | 当前值 | 含义 |
|---|---:|---|
| `RISK_FREE_RATE` | 0.015 | 固定无风险利率 |
| `HALF_SKEW_H` | 0.1 | Half-Skew的log-moneyness锚点 |
| `STRATEGY_MAX_OPTIONS` | 9 | 每日每期限最多选择的期权数 |
| `STRATEGY_POSITION_BOUND` | 100 | 单腿期权仓位绝对上限 |
| `STRATEGY_MAX_DAILY_TRADE_PER_LEG` | 30 | 单腿单日最大仓位变化 |
| `STRATEGY_RIDGE` | \(10^{-5}\) | L2仓位正则强度 |
| `STRATEGY_CAPITAL_PENALTY` | \(10^{-5}\) | 资金占用惩罚强度 |
| `STRATEGY_OPTION_MULTIPLIER` | 100 | 期权合约乘数 |
| `STRATEGY_FUTURES_MULTIPLIER` | 200 | 期货合约乘数 |

## 输出结果

运行结果保存在 `outputs/` 目录，主要包括：

- 标准化行情数据；
- 每日 Forward、Repo 和 IV 曲线参数；
- Call Skew、Put Skew 与 Wing Curvature 期限结构；
- 各期限每日持仓和交易记录；
- 期权及期货资金占用；
- 每日与累计 PnL；
- Traditional Taylor 和完整二阶 Taylor 归因；
- 各期限累计归因图及汇总统计表。

每个期限的核心结果位于：

```text
outputs/06_skew_strategy_QUADRATIC_HALF-SKEW_CURVATURE-WING/expiry_XXXX/
```

其中：

| 文件 | 内容 |
|---|---|
| `positions.csv` | 每日持仓 |
| `daily_account_pnl.csv` | 市场收益、手续费与实际收益 |
| `total_margin_daily.csv` | 每日总资金占用 |
| `traditional_taylor_attribution.csv` | Traditional Taylor PnL归因 |
| `t2_attribution.csv` | 完整二阶Taylor PnL归因 |
| `figures/` | PnL、资金占用和归因图片 |

