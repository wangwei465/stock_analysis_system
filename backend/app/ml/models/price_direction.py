"""
价格方向预测模型
使用LightGBM进行分类预测
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pickle
import os

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from app.ml.features import FeatureEngineer


class PriceDirectionModel:
    """价格方向预测模型"""

    def __init__(
        self,
        forward_days: int = 5,
        threshold: float = 0.0,
        model_params: Dict = None
    ):
        """
        初始化模型

        Args:
            forward_days: 预测未来天数
            threshold: 方向判断阈值 (0表示纯涨跌，>0表示需要超过阈值才算涨)
            model_params: LightGBM参数
        """
        self.forward_days = forward_days
        self.threshold = threshold
        self.model = None
        self.feature_names = None
        self.feature_importance = None

        # 默认模型参数
        self.model_params = model_params or {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_child_samples': 20,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42
        }

    def prepare_data(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        准备训练数据

        Args:
            df: 原始OHLCV数据
            train_ratio: 训练集比例

        Returns:
            X_train, y_train, X_test, y_test
        """
        # 生成特征
        features = FeatureEngineer.generate_all_features(df)

        # 生成标签
        direction, _, _ = FeatureEngineer.create_labels(
            df,
            forward_days=self.forward_days,
            threshold=self.threshold
        )

        # 合并并删除缺失值
        data = pd.concat([features, direction.rename('target')], axis=1)
        data = data.dropna()

        # 时序分割 (避免数据泄露)
        split_idx = int(len(data) * train_ratio)
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]

        X_train = train_data.drop('target', axis=1)
        y_train = train_data['target']
        X_test = test_data.drop('target', axis=1)
        y_test = test_data['target']

        self.feature_names = X_train.columns.tolist()

        return X_train, y_train, X_test, y_test

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50
    ) -> Dict:
        """
        训练模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
            num_boost_round: 最大迭代次数
            early_stopping_rounds: 早停轮数

        Returns:
            训练结果信息
        """
        if not HAS_LIGHTGBM:
            raise ImportError("LightGBM is not installed. Please install it with: pip install lightgbm")

        train_data = lgb.Dataset(X_train, label=y_train)

        valid_sets = [train_data]
        valid_names = ['train']

        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val)
            valid_sets.append(val_data)
            valid_names.append('valid')

        # 训练模型
        callbacks = [lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=False)]

        self.model = lgb.train(
            self.model_params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )

        # 保存特征重要性
        self.feature_importance = dict(zip(
            self.feature_names,
            self.model.feature_importance(importance_type='gain')
        ))

        # 计算训练指标
        train_pred = self.model.predict(X_train)
        train_pred_binary = (train_pred > 0.5).astype(int)
        train_accuracy = (train_pred_binary == y_train).mean()

        result = {
            'train_accuracy': float(train_accuracy),
            'best_iteration': self.model.best_iteration,
            'feature_count': len(self.feature_names)
        }

        if X_val is not None and y_val is not None:
            val_pred = self.model.predict(X_val)
            val_pred_binary = (val_pred > 0.5).astype(int)
            val_accuracy = (val_pred_binary == y_val).mean()
            result['val_accuracy'] = float(val_accuracy)

        return result

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测

        Args:
            X: 特征DataFrame

        Returns:
            predictions: 预测概率
            directions: 预测方向 (1=上涨, 0=下跌)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # 确保特征顺序一致
        X = X[self.feature_names]

        predictions = self.model.predict(X)
        directions = (predictions > 0.5).astype(int)

        return predictions, directions

    def predict_single(self, df: pd.DataFrame) -> Dict:
        """
        预测单只股票

        Args:
            df: 包含OHLCV的DataFrame (至少需要60天数据)

        Returns:
            预测结果字典
        """
        if len(df) < 60:
            raise ValueError("Need at least 60 days of data for prediction")

        # 生成特征
        features = FeatureEngineer.generate_all_features(df)

        # 取最后一行(最新数据)的特征
        latest_features = features.iloc[[-1]].dropna(axis=1)

        # 确保所有需要的特征都存在
        missing_features = set(self.feature_names) - set(latest_features.columns)
        if missing_features:
            # 用0填充缺失特征
            for f in missing_features:
                latest_features[f] = 0

        latest_features = latest_features[self.feature_names]

        # 预测
        prob, direction = self.predict(latest_features)

        return {
            'probability': float(prob[0]),
            'direction': int(direction[0]),
            'direction_label': '上涨' if direction[0] == 1 else '下跌',
            'confidence': float(abs(prob[0] - 0.5) * 2),  # 0-1的置信度
            'forward_days': self.forward_days
        }

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """
        评估模型

        Args:
            X_test: 测试特征
            y_test: 测试标签

        Returns:
            评估指标字典
        """
        predictions, directions = self.predict(X_test)

        # 准确率
        accuracy = (directions == y_test).mean()

        # 精确率、召回率、F1
        tp = ((directions == 1) & (y_test == 1)).sum()
        fp = ((directions == 1) & (y_test == 0)).sum()
        fn = ((directions == 0) & (y_test == 1)).sum()
        tn = ((directions == 0) & (y_test == 0)).sum()

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        # AUC
        try:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(y_test, predictions)
        except:
            auc = None

        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'auc': float(auc) if auc else None,
            'confusion_matrix': {
                'tp': int(tp),
                'fp': int(fp),
                'fn': int(fn),
                'tn': int(tn)
            }
        }

    def get_top_features(self, n: int = 20) -> List[Dict]:
        """
        获取最重要的特征

        Args:
            n: 返回特征数量

        Returns:
            特征重要性列表
        """
        if self.feature_importance is None:
            return []

        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]

        return [
            {'feature': f, 'importance': float(i)}
            for f, i in sorted_features
        ]

    def save(self, filepath: str):
        """保存模型"""
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance,
            'forward_days': self.forward_days,
            'threshold': self.threshold,
            'model_params': self.model_params
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    def load(self, filepath: str):
        """加载模型"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.feature_importance = model_data['feature_importance']
        self.forward_days = model_data['forward_days']
        self.threshold = model_data['threshold']
        self.model_params = model_data['model_params']


class QuickPredictionModel:
    """
    快速预测模型（无需训练）
    基于技术指标的简单规则预测
    """

    @staticmethod
    def predict(df: pd.DataFrame) -> Dict:
        """
        基于技术指标的快速预测

        Args:
            df: 包含OHLCV的DataFrame

        Returns:
            预测结果
        """
        if len(df) < 60:
            return {
                'direction': 0,
                'direction_label': '数据不足',
                'confidence': 0,
                'signals': {}
            }

        signals = {}
        scores = []

        # 1. MA趋势信号
        ma_df = FeatureEngineer.calculate_technical_features(df)
        latest = df.iloc[-1]

        if 'ma5_ma20_cross' in ma_df.columns:
            ma_signal = ma_df['ma5_ma20_cross'].iloc[-1]
            signals['ma_trend'] = '多头排列' if ma_signal == 1 else '空头排列'
            scores.append(1 if ma_signal == 1 else -1)

        # 2. RSI信号
        if 'rsi_14' in ma_df.columns:
            rsi = ma_df['rsi_14'].iloc[-1]
            if rsi > 70:
                signals['rsi'] = '超买'
                scores.append(-0.5)
            elif rsi < 30:
                signals['rsi'] = '超卖'
                scores.append(0.5)
            elif rsi > 50:
                signals['rsi'] = '偏强'
                scores.append(0.3)
            else:
                signals['rsi'] = '偏弱'
                scores.append(-0.3)

        # 3. MACD信号
        if 'macd_hist' in ma_df.columns:
            macd_hist = ma_df['macd_hist'].iloc[-1]
            macd_hist_prev = ma_df['macd_hist'].iloc[-2] if len(ma_df) > 1 else 0

            if macd_hist > 0 and macd_hist > macd_hist_prev:
                signals['macd'] = '红柱增长'
                scores.append(1)
            elif macd_hist > 0:
                signals['macd'] = '红柱缩短'
                scores.append(0.3)
            elif macd_hist < 0 and macd_hist < macd_hist_prev:
                signals['macd'] = '绿柱增长'
                scores.append(-1)
            else:
                signals['macd'] = '绿柱缩短'
                scores.append(-0.3)

        # 4. KDJ信号
        if 'kdj_k' in ma_df.columns and 'kdj_d' in ma_df.columns:
            k = ma_df['kdj_k'].iloc[-1]
            d = ma_df['kdj_d'].iloc[-1]

            if k > d and k < 80:
                signals['kdj'] = '金叉'
                scores.append(0.5)
            elif k < d and k > 20:
                signals['kdj'] = '死叉'
                scores.append(-0.5)
            elif k > 80:
                signals['kdj'] = '超买区'
                scores.append(-0.3)
            elif k < 20:
                signals['kdj'] = '超卖区'
                scores.append(0.3)
            else:
                signals['kdj'] = '中性'
                scores.append(0)

        # 5. 成交量信号
        vol_features = FeatureEngineer.calculate_volume_features(df)
        if 'volume_ratio_5d' in vol_features.columns:
            vol_ratio = vol_features['volume_ratio_5d'].iloc[-1]
            if vol_ratio > 2:
                signals['volume'] = '放量'
                # 配合价格方向
                price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
                scores.append(0.5 if price_change > 0 else -0.5)
            elif vol_ratio < 0.5:
                signals['volume'] = '缩量'
                scores.append(0)
            else:
                signals['volume'] = '平量'
                scores.append(0)

        # 计算综合得分
        if scores:
            avg_score = sum(scores) / len(scores)
            confidence = min(abs(avg_score), 1)

            if avg_score > 0.3:
                direction = 1
                direction_label = '看涨'
            elif avg_score < -0.3:
                direction = -1
                direction_label = '看跌'
            else:
                direction = 0
                direction_label = '震荡'
        else:
            avg_score = 0
            confidence = 0
            direction = 0
            direction_label = '无法判断'

        return {
            'direction': direction,
            'direction_label': direction_label,
            'confidence': float(confidence),
            'score': float(avg_score),
            'signals': signals
        }
