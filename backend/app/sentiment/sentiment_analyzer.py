"""
情感分析模块
用于分析股票相关新闻的情感倾向
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# Lazy import AKShare
_ak = None
HAS_AKSHARE = True

def get_akshare():
    global _ak, HAS_AKSHARE
    if _ak is None:
        try:
            import akshare as ak
            _ak = ak
        except ImportError:
            HAS_AKSHARE = False
            _ak = None
    return _ak


class SentimentLevel(Enum):
    """情感级别"""
    VERY_POSITIVE = 2
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1
    VERY_NEGATIVE = -2


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    content: Optional[str]
    source: str
    publish_time: Optional[str]
    url: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None


class StockNewsFetcher:
    """
    股票新闻获取器
    使用AKShare获取A股相关新闻
    """

    @staticmethod
    def get_stock_news(stock_code: str, limit: int = 20) -> List[NewsItem]:
        """
        获取个股新闻

        Args:
            stock_code: 股票代码
            limit: 返回条数

        Returns:
            新闻列表
        """
        if not HAS_AKSHARE:
            return []

        news_list = []

        try:
            # 获取个股新闻
            # 注意: 需要去掉前缀如 sh/sz
            code = stock_code.replace('sh', '').replace('sz', '').replace('.', '')

            ak = get_akshare()
            if ak is None:
                return []
            df = ak.stock_news_em(symbol=code)

            if df is not None and not df.empty:
                for _, row in df.head(limit).iterrows():
                    news_list.append(NewsItem(
                        title=row.get('新闻标题', ''),
                        content=row.get('新闻内容', ''),
                        source=row.get('新闻来源', ''),
                        publish_time=row.get('发布时间', ''),
                        url=row.get('新闻链接', '')
                    ))

        except Exception as e:
            print(f"Error fetching stock news: {e}")

        return news_list

    @staticmethod
    def get_market_news(limit: int = 20) -> List[NewsItem]:
        """
        获取市场新闻

        Returns:
            新闻列表
        """
        if not HAS_AKSHARE:
            return []

        news_list = []

        try:
            # 财经新闻 - 使用财联社电报
            ak = get_akshare()
            if ak is None:
                return []
            df = ak.stock_info_global_cls(symbol='全部')

            if df is not None and not df.empty:
                for _, row in df.head(limit).iterrows():
                    # 获取列名（可能有编码问题，使用索引位置）
                    cols = df.columns.tolist()
                    title = row[cols[0]] if len(cols) > 0 else ''
                    content = row[cols[1]] if len(cols) > 1 else ''
                    publish_date = row[cols[2]] if len(cols) > 2 else ''
                    publish_time = row[cols[3]] if len(cols) > 3 else ''

                    # 组合日期和时间
                    time_str = f"{publish_date} {publish_time}" if publish_date and publish_time else ''

                    news_list.append(NewsItem(
                        title=str(title),
                        content=str(content),
                        source='财联社',
                        publish_time=time_str
                    ))

        except Exception as e:
            print(f"Error fetching market news: {e}")

        return news_list


class ChineseSentimentAnalyzer:
    """
    中文情感分析器
    基于词典的简单情感分析
    """

    # 积极词汇
    POSITIVE_WORDS = [
        '涨', '涨停', '大涨', '暴涨', '上涨', '上升', '走高', '反弹', '拉升',
        '突破', '创新高', '新高', '强势', '利好', '利多', '看涨', '看好',
        '增长', '增加', '提升', '上调', '超预期', '业绩大增', '净利润增长',
        '回暖', '复苏', '繁荣', '景气', '乐观', '向好', '好转',
        '机构买入', '大单买入', '资金流入', '北向资金买入', '主力增仓',
        '利润', '盈利', '分红', '回购', '增持', '入选', '中标',
        '合作', '签约', '收购', '扩产', '突破', '创新', '研发成功'
    ]

    # 消极词汇
    NEGATIVE_WORDS = [
        '跌', '跌停', '大跌', '暴跌', '下跌', '下降', '走低', '回落', '下挫',
        '破位', '创新低', '新低', '弱势', '利空', '利淡', '看跌', '看空',
        '下滑', '减少', '下调', '低于预期', '业绩下滑', '净利润下降',
        '亏损', '巨亏', '爆雷', '暴雷', '风险', '警示', '退市',
        '机构卖出', '大单卖出', '资金流出', '北向资金卖出', '主力减仓',
        '减持', '清仓', '质押', '违规', '处罚', '调查', '立案',
        '诉讼', '纠纷', '解约', '终止', '延期', '推迟'
    ]

    # 程度副词
    DEGREE_WORDS = {
        '非常': 1.5, '十分': 1.5, '极其': 2.0, '极度': 2.0,
        '特别': 1.3, '相当': 1.2, '比较': 0.8, '稍微': 0.5,
        '大幅': 1.5, '巨幅': 2.0, '小幅': 0.5
    }

    # 否定词
    NEGATION_WORDS = ['不', '没', '无', '非', '未', '否']

    @classmethod
    def analyze_text(cls, text: str) -> Dict:
        """
        分析文本情感

        Args:
            text: 待分析文本

        Returns:
            情感分析结果
        """
        if not text:
            return {
                'score': 0,
                'label': '中性',
                'level': SentimentLevel.NEUTRAL.value,
                'positive_words': [],
                'negative_words': []
            }

        text = text.lower()
        positive_found = []
        negative_found = []
        score = 0

        # 检测积极词汇
        for word in cls.POSITIVE_WORDS:
            if word in text:
                positive_found.append(word)
                word_score = 1.0

                # 检查程度副词
                for degree_word, multiplier in cls.DEGREE_WORDS.items():
                    if degree_word + word in text or degree_word in text[:text.find(word)]:
                        word_score *= multiplier
                        break

                # 检查否定词
                for neg in cls.NEGATION_WORDS:
                    if neg + word in text:
                        word_score *= -1
                        break

                score += word_score

        # 检测消极词汇
        for word in cls.NEGATIVE_WORDS:
            if word in text:
                negative_found.append(word)
                word_score = -1.0

                # 检查程度副词
                for degree_word, multiplier in cls.DEGREE_WORDS.items():
                    if degree_word + word in text or degree_word in text[:text.find(word)]:
                        word_score *= multiplier
                        break

                # 检查否定词
                for neg in cls.NEGATION_WORDS:
                    if neg + word in text:
                        word_score *= -1
                        break

                score += word_score

        # 归一化得分 (-1 到 1)
        if positive_found or negative_found:
            max_possible = len(positive_found) + len(negative_found)
            score = score / max_possible if max_possible > 0 else 0
            score = max(-1, min(1, score))

        # 确定标签
        if score >= 0.5:
            label = '非常积极'
            level = SentimentLevel.VERY_POSITIVE
        elif score >= 0.2:
            label = '积极'
            level = SentimentLevel.POSITIVE
        elif score <= -0.5:
            label = '非常消极'
            level = SentimentLevel.VERY_NEGATIVE
        elif score <= -0.2:
            label = '消极'
            level = SentimentLevel.NEGATIVE
        else:
            label = '中性'
            level = SentimentLevel.NEUTRAL

        return {
            'score': float(score),
            'label': label,
            'level': level.value,
            'positive_words': list(set(positive_found)),
            'negative_words': list(set(negative_found))
        }

    @classmethod
    def analyze_news_list(cls, news_list: List[NewsItem]) -> Dict:
        """
        分析新闻列表的整体情感

        Args:
            news_list: 新闻列表

        Returns:
            整体情感分析结果
        """
        if not news_list:
            return {
                'overall_score': 0,
                'overall_label': '无数据',
                'news_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'analyzed_news': []
            }

        analyzed = []
        scores = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for news in news_list:
            # 分析标题和内容
            text = (news.title or '') + ' ' + (news.content or '')
            result = cls.analyze_text(text)

            news.sentiment_score = result['score']
            news.sentiment_label = result['label']

            scores.append(result['score'])

            if result['level'] > 0:
                positive_count += 1
            elif result['level'] < 0:
                negative_count += 1
            else:
                neutral_count += 1

            analyzed.append({
                'title': news.title,
                'source': news.source,
                'publish_time': news.publish_time,
                'sentiment': result
            })

        # 计算整体得分
        overall_score = sum(scores) / len(scores) if scores else 0

        if overall_score >= 0.3:
            overall_label = '整体积极'
        elif overall_score <= -0.3:
            overall_label = '整体消极'
        else:
            overall_label = '整体中性'

        return {
            'overall_score': float(overall_score),
            'overall_label': overall_label,
            'news_count': len(news_list),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_distribution': {
                'positive': positive_count / len(news_list) * 100,
                'negative': negative_count / len(news_list) * 100,
                'neutral': neutral_count / len(news_list) * 100
            },
            'analyzed_news': analyzed[:10]  # 只返回前10条
        }


class SentimentAnalysisService:
    """
    情感分析服务
    整合新闻获取和情感分析
    """

    def __init__(self):
        self.news_fetcher = StockNewsFetcher()
        self.analyzer = ChineseSentimentAnalyzer()

    def analyze_stock_sentiment(self, stock_code: str, limit: int = 20) -> Dict:
        """
        分析个股情感

        Args:
            stock_code: 股票代码
            limit: 新闻条数

        Returns:
            情感分析结果
        """
        # 获取新闻
        news_list = self.news_fetcher.get_stock_news(stock_code, limit)

        if not news_list:
            return {
                'stock_code': stock_code,
                'status': 'no_news',
                'message': '未获取到相关新闻',
                'overall_score': 0,
                'overall_label': '无数据'
            }

        # 分析情感
        result = self.analyzer.analyze_news_list(news_list)
        result['stock_code'] = stock_code
        result['status'] = 'success'

        return result

    def analyze_market_sentiment(self, limit: int = 30) -> Dict:
        """
        分析市场整体情感

        Args:
            limit: 新闻条数

        Returns:
            市场情感分析结果
        """
        # 获取市场新闻
        news_list = self.news_fetcher.get_market_news(limit)

        if not news_list:
            return {
                'status': 'no_news',
                'message': '未获取到市场新闻',
                'overall_score': 0,
                'overall_label': '无数据'
            }

        # 分析情感
        result = self.analyzer.analyze_news_list(news_list)
        result['status'] = 'success'

        return result

    def get_sentiment_summary(self, stock_code: str) -> Dict:
        """
        获取情感摘要

        Args:
            stock_code: 股票代码

        Returns:
            情感摘要
        """
        stock_sentiment = self.analyze_stock_sentiment(stock_code, 15)
        market_sentiment = self.analyze_market_sentiment(15)

        # 综合评估
        stock_score = stock_sentiment.get('overall_score', 0)
        market_score = market_sentiment.get('overall_score', 0)

        # 70%个股权重 + 30%市场权重
        combined_score = stock_score * 0.7 + market_score * 0.3

        if combined_score >= 0.3:
            combined_label = '看涨情绪'
            color = 'green'
        elif combined_score <= -0.3:
            combined_label = '看跌情绪'
            color = 'red'
        else:
            combined_label = '情绪中性'
            color = 'gray'

        return {
            'stock_code': stock_code,
            'stock_sentiment': {
                'score': stock_sentiment.get('overall_score', 0),
                'label': stock_sentiment.get('overall_label', '无数据'),
                'news_count': stock_sentiment.get('news_count', 0)
            },
            'market_sentiment': {
                'score': market_sentiment.get('overall_score', 0),
                'label': market_sentiment.get('overall_label', '无数据'),
                'news_count': market_sentiment.get('news_count', 0)
            },
            'combined': {
                'score': float(combined_score),
                'label': combined_label,
                'color': color
            },
            'recommendation': self._get_sentiment_recommendation(combined_score),
            'top_news': stock_sentiment.get('analyzed_news', [])[:5]
        }

    def _get_sentiment_recommendation(self, score: float) -> str:
        """根据情感得分生成建议"""
        if score >= 0.5:
            return '市场情绪非常乐观，利好消息较多，但需注意追高风险'
        elif score >= 0.2:
            return '市场情绪偏向积极，可关注潜在机会'
        elif score <= -0.5:
            return '市场情绪非常悲观，利空消息较多，建议谨慎操作'
        elif score <= -0.2:
            return '市场情绪偏向消极，注意风险控制'
        else:
            return '市场情绪中性，建议观望等待明确方向'
