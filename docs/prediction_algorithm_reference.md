# Intelligent Prediction Algorithm Technical Reference

## Quick Reference Card

### Signal Weights

| Module | Weight | Key Indicators |
|--------|--------|----------------|
| Technical | 30% | RSI, MACD, KDJ, Bollinger |
| Trend | 25% | MA Array, Slope, Linear Regression |
| Momentum | 20% | Returns, ROC, Acceleration |
| Volatility | 15% | Annual Vol, Vol Change |
| Volume | 10% | Volume Ratio, Price-Volume |

---

### RSI Signals

```
RSI < 30  → Oversold  → BUY  (+0.4)
RSI > 70  → Overbought → SELL (-0.4)
RSI < 45 & rising   → Low Recovery  (+0.2)
RSI > 55 & falling  → High Pullback (-0.2)
```

---

### MACD Signals

```
DIF crosses above DEA → Golden Cross → BUY  (+0.5)
DIF crosses below DEA → Death Cross  → SELL (-0.5)
Histogram expanding (positive) → BUY  (+0.2)
Histogram expanding (negative) → SELL (-0.2)
```

---

### KDJ Signals

```
J < 0    → Oversold   → BUY  (+0.3)
J > 100  → Overbought → SELL (-0.3)
K > D (K < 50) → Low Golden Cross → BUY  (+0.3)
K < D (K > 50) → High Death Cross → SELL (-0.3)
```

---

### Bollinger Bands

```
Price <= Lower Band → Support Hit → BUY  (+0.3)
Price >= Upper Band → Resistance Hit → SELL (-0.3)
```

---

### MA Trend

```
MA5 > MA10 > MA20 > MA60 → Bull Alignment → BUY  (+0.5)
MA5 < MA10 < MA20 < MA60 → Bear Alignment → SELL (-0.5)
Price > MA20 → Uptrend   → BUY  (+0.2)
Price < MA20 → Downtrend → SELL (-0.2)
```

---

### Volume Signals

```
Volume Ratio > 2 & Price Up > 2%   → Volume Surge Up   → BUY  (+0.4)
Volume Ratio > 2 & Price Down > 2% → Volume Surge Down → SELL (-0.4)
Volume Ratio < 0.5 & Price Up      → Light Volume Up   → BUY  (+0.1)
Volume Ratio < 0.5 & Price Down    → Light Volume Down → SELL (-0.1)
```

---

### Signal Thresholds (Moderate Risk)

| Score Range | Signal | Action |
|-------------|--------|--------|
| ≥ 0.8 | Strong Buy | Aggressive entry |
| ≥ 0.4 | Buy | Normal entry |
| -0.4 ~ 0.4 | Hold/Wait | No action |
| ≤ -0.4 | Sell | Normal exit |
| ≤ -0.8 | Strong Sell | Aggressive exit |

---

### Stop Loss / Take Profit (ATR-based)

| Risk Level | Stop Loss | Take Profit | R/R Ratio |
|------------|-----------|-------------|-----------|
| Conservative | 1.5 × ATR | 2.0 × ATR | 1.33 |
| Moderate | 2.0 × ATR | 3.0 × ATR | 1.50 |
| Aggressive | 2.5 × ATR | 4.0 × ATR | 1.60 |

---

### Price Range Prediction

```python
# Forward Volatility (Square Root of Time)
σ_forward = σ_daily × √(forward_days)

# Confidence Intervals
Lower = Price × (1 - Z × σ_forward)
Upper = Price × (1 + Z × σ_forward)

# Z-values
68% confidence: Z = 1.00
90% confidence: Z = 1.645
95% confidence: Z = 1.96
99% confidence: Z = 2.576
```

---

### Risk Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Daily Vol | std(returns) | Daily price swing |
| Annual Vol | Daily Vol × √252 | Yearly risk level |
| Max Drawdown | (Peak - Current) / Peak | Worst loss from peak |
| VaR 95% | 5th percentile of returns | Max loss at 95% confidence |
| CVaR 95% | Mean of returns < VaR | Expected loss in worst 5% |

---

### Volatility Classification

| Annual Volatility | Level | Risk |
|-------------------|-------|------|
| > 40% | High | Risky |
| 20% - 40% | Medium | Moderate |
| < 20% | Low | Stable |

---

### Recommendation Matrix

| Combined Score | Action | Risk Level |
|----------------|--------|------------|
| > 0.5 | Active Buy | Medium |
| 0.2 ~ 0.5 | Moderate Buy | Low |
| -0.2 ~ 0.2 | Wait | Low |
| -0.5 ~ -0.2 | Reduce | Medium |
| < -0.5 | Sell | High |

---

### Technical Indicator Formulas

**Moving Average**
```
MA(N) = Σ(Close_i) / N
```

**MACD**
```
DIF = EMA(12) - EMA(26)
DEA = EMA(DIF, 9)
MACD_Histogram = (DIF - DEA) × 2
```

**RSI**
```
RS = Avg_Gain / Avg_Loss
RSI = 100 - 100 / (1 + RS)
```

**KDJ**
```
RSV = (Close - Low_N) / (High_N - Low_N) × 100
K = EMA(RSV, 3)
D = EMA(K, 3)
J = 3K - 2D
```

**Bollinger Bands**
```
Middle = MA(20)
Upper = Middle + 2 × StdDev(20)
Lower = Middle - 2 × StdDev(20)
```

**ATR**
```
TR = max(H-L, |H-Prev_C|, |L-Prev_C|)
ATR = MA(TR, 14)
```

---

### Data Requirements

- Minimum: 60 trading days
- Fields: open, high, low, close, volume
- Frequency: Daily

---

### API Endpoint

```
GET /api/v1/ml/comprehensive/{stock_code}

Parameters:
- forward_days: int (1-20, default: 5)
- include_sentiment: bool (default: true)

Response: ComprehensivePrediction
```

---

*Version 1.0.0 | Last Updated: 2024-01*
