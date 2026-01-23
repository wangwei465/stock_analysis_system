"""
情感分析模块
用于分析股票相关新闻的情感倾向
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 延迟导入 AKShare（可选依赖）：
# - 部署环境未安装 akshare 时，不让整个服务启动失败，而是将情绪分析相关接口降级为“无数据”。
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
            # 注意：AKShare 的 stock_news_em 接口一般需要传“纯数字代码”，
            # 因此这里把可能出现的 `sh/sz` 前缀、`.` 等分隔符都清理掉。
            code = stock_code.replace('sh', '').replace('sz', '').replace('.', '')

            ak = get_akshare()
            if ak is None:
                return []
            # AKShare: stock_news_em 返回个股相关新闻列表，常见字段包括：
            # - 新闻标题、新闻内容、新闻来源、发布时间、新闻链接
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
            # AKShare: stock_info_global_cls 获取财联社电报资讯。
            # 传参 symbol='全部' 表示拉取全量资讯，随后再按 limit 截断。
            df = ak.stock_info_global_cls(symbol='全部')

            if df is not None and not df.empty:
                for _, row in df.head(limit).iterrows():
                    # 获取列名（不同环境/版本可能存在差异），这里使用“索引位置”读取更稳妥。
                    # 约定：前几列依次为 标题/内容/日期/时间（若接口变更，可在此处调整索引映射）。
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
    ====================================
    基于词典的金融文本情感分析工具。

    核心功能：
    - 识别积极/消极词汇并计算情感得分
    - 支持程度副词修饰（如"非常"、"极其"）
    - 支持否定词处理（如"不涨"转为消极）
    - 支持金融专业术语和短语识别

    使用示例：
    >>> analyzer = ChineseSentimentAnalyzer()
    >>> result = analyzer.analyze_text("股价大涨突破新高，成交量放大")
    >>> print(result['label'])  # 输出: '积极' 或 '非常积极'
    """

    # =========================================================================
    # 积极词汇词典（200+词汇）
    # =========================================================================
    # 按类别组织，便于维护和扩展
    POSITIVE_WORDS = [
        # ----- 价格上涨类 -----
        '涨', '涨停', '大涨', '暴涨', '上涨', '上升', '走高', '反弹', '拉升',
        '攀升', '跳涨', '飙升', '涨幅', '翻红', '翻番', '翻倍', '上扬', '走强',
        '冲高', '回升', '企稳回升', '止跌回升', '触底反弹', '绝地反击', 'V型反转',

        # ----- 突破创新类 -----
        '突破', '创新高', '新高', '历史新高', '阶段新高', '年内新高',
        '突破前高', '突破压力', '向上突破', '放量突破', '有效突破',

        # ----- 趋势强势类 -----
        '强势', '强劲', '坚挺', '稳健', '稳中向好', '稳步上升', '持续走强',
        '多头', '多头排列', '牛市', '牛股', '龙头', '领涨', '逆势上涨',

        # ----- 利好消息类 -----
        '利好', '利多', '看涨', '看好', '看多', '做多', '加仓', '建仓',
        '重仓', '满仓', '超配', '推荐买入', '强烈推荐', '投资机会',
        '买入评级', '增持评级', '目标价上调',

        # ----- 业绩增长类 -----
        '增长', '增加', '提升', '上调', '超预期', '业绩大增', '净利润增长',
        '营收增长', '盈利增长', '高增长', '翻番增长', '同比增长', '环比增长',
        '业绩暴增', '业绩翻倍', '扭亏为盈', '业绩超预期', '业绩快报向好',

        # ----- 经济复苏类 -----
        '回暖', '复苏', '繁荣', '景气', '乐观', '向好', '好转', '改善',
        '企稳', '触底', '见底', '筑底成功', '底部确认', '止跌企稳',
        '经济复苏', '需求回暖', '行业复苏', '消费回暖',

        # ----- 资金流入类 -----
        '机构买入', '大单买入', '资金流入', '北向资金买入', '主力增仓',
        '北向净买入', '外资加仓', '主力资金流入', '融资买入', '融资余额增加',
        '净买入', '大笔买入', '机构增持', '基金增仓', '社保基金买入',
        'QFII买入', '险资买入', '养老金买入',

        # ----- 分红回报类 -----
        '利润', '盈利', '分红', '回购', '增持', '高送转', '派息',
        '现金分红', '股息率', '高股息', '分红预案', '股票回购',

        # ----- 商业合作类 -----
        '入选', '中标', '合作', '签约', '收购', '扩产', '创新', '研发成功',
        '战略合作', '重大合同', '订单增加', '大单签约', '框架协议',
        '并购重组', '资产注入', '借壳上市', '整体上市',

        # ----- 政策支持类 -----
        '政策利好', '政策支持', '减税降费', '补贴', '扶持', '刺激',
        '降准', '降息', '宽松', '流动性充裕', '央行放水',

        # ----- 技术指标类 -----
        '金叉', 'MACD金叉', 'KDJ金叉', '均线多头', '放量上涨',
        '底部放量', '突破均线', '站上均线', '量价齐升', '量能放大',

        # ----- 评级相关 -----
        '首次覆盖买入', '维持买入', '上调评级', '首次推荐',
        '强烈买入', '优于大市', '跑赢大盘',
    ]

    # =========================================================================
    # 消极词汇词典（200+词汇）
    # =========================================================================
    NEGATIVE_WORDS = [
        # ----- 价格下跌类 -----
        '跌', '跌停', '大跌', '暴跌', '下跌', '下降', '走低', '回落', '下挫',
        '跳水', '崩盘', '闪崩', '跌幅', '翻绿', '杀跌', '砸盘', '跌破',
        '一字跌停', '连续跌停', '重挫', '急跌', '断崖式下跌',

        # ----- 破位创低类 -----
        '破位', '创新低', '新低', '历史新低', '阶段新低', '年内新低',
        '跌破支撑', '跌破均线', '有效破位', '破位下行',

        # ----- 趋势弱势类 -----
        '弱势', '疲软', '低迷', '萎靡', '持续走弱', '阴跌', '绵绵下跌',
        '空头', '空头排列', '熊市', '熊股', '领跌', '补跌', '加速下跌',

        # ----- 利空消息类 -----
        '利空', '利淡', '看跌', '看空', '做空', '减仓', '清仓', '斩仓',
        '止损', '割肉', '抛售', '出逃', '卖出评级', '减持评级',
        '目标价下调', '评级下调',

        # ----- 业绩下滑类 -----
        '下滑', '减少', '下调', '低于预期', '业绩下滑', '净利润下降',
        '营收下降', '盈利下滑', '负增长', '同比下降', '环比下降',
        '业绩不及预期', '业绩爆雷', '业绩变脸', '业绩预警',

        # ----- 亏损风险类 -----
        '亏损', '巨亏', '爆雷', '暴雷', '风险', '警示', '退市', '摘牌',
        'ST', '*ST', '风险警示', '退市风险', '暂停上市', '终止上市',
        '财务造假', '商誉减值', '资产减值', '坏账损失',

        # ----- 资金流出类 -----
        '机构卖出', '大单卖出', '资金流出', '北向资金卖出', '主力减仓',
        '北向净卖出', '外资减仓', '主力资金流出', '融资卖出', '融资余额减少',
        '净卖出', '大笔卖出', '机构减持', '基金减仓', '清仓式减持',
        '股东减持', '高管减持', '限售股解禁',

        # ----- 监管处罚类 -----
        '减持', '清仓', '质押', '违规', '处罚', '调查', '立案',
        '行政处罚', '监管函', '问询函', '关注函', '警示函',
        '证监会调查', '交易所问询', '被立案', '涉嫌违法',

        # ----- 诉讼纠纷类 -----
        '诉讼', '纠纷', '解约', '终止', '延期', '推迟', '违约',
        '债务违约', '债券违约', '信用违约', '破产', '重整',

        # ----- 经济衰退类 -----
        '衰退', '萧条', '低迷', '疲弱', '恶化', '下行', '承压',
        '需求萎缩', '行业下行', '消费疲软', '经济放缓',

        # ----- 技术指标类 -----
        '死叉', 'MACD死叉', 'KDJ死叉', '均线空头', '放量下跌',
        '天量见天价', '跌破均线', '量价背离', '量能萎缩',

        # ----- 市场恐慌类 -----
        '恐慌', '踩踏', '抛压', '套牢', '被套', '深套', '割肉盘',
        '黑天鹅', '灰犀牛', '系统性风险', '市场崩溃',
    ]

    # =========================================================================
    # 程度副词词典
    # =========================================================================
    # 权重说明：>1 表示加强语气，<1 表示减弱语气
    DEGREE_WORDS = {
        # 极度加强（权重 2.0）
        '极其': 2.0, '极度': 2.0, '极为': 2.0, '异常': 2.0,

        # 强烈加强（权重 1.5-1.8）
        '非常': 1.5, '十分': 1.5, '相当': 1.5, '特别': 1.5,
        '大幅': 1.5, '巨幅': 1.8, '急剧': 1.5, '剧烈': 1.5,
        '显著': 1.3, '明显': 1.3, '严重': 1.5, '重大': 1.3,

        # 一般加强（权重 1.2-1.3）
        '很': 1.2, '太': 1.2, '更': 1.2, '更加': 1.2,
        '越来越': 1.3, '愈发': 1.3, '日益': 1.2,

        # 减弱程度（权重 <1）
        '比较': 0.8, '较': 0.8, '稍': 0.6, '稍微': 0.5,
        '略微': 0.5, '小幅': 0.5, '轻微': 0.5, '些许': 0.5,
        '有些': 0.6, '有点': 0.6, '微幅': 0.4,
    }

    # =========================================================================
    # 否定词词典
    # =========================================================================
    NEGATION_WORDS = ['不', '没', '无', '非', '未', '否', '难', '难以', '未能', '不再', '并非', '尚未']

    # =========================================================================
    # 金融短语词典（组合词汇，有特殊含义）
    # =========================================================================
    # 格式: {'短语': 得分}，正分表示积极，负分表示消极
    PHRASE_DICT = {
        # ----- 积极短语 -----
        '放量突破': 1.5,
        '底部放量': 1.3,
        '量价齐升': 1.4,
        '创历史新高': 1.6,
        '业绩大增': 1.5,
        '扭亏为盈': 1.5,
        '超预期增长': 1.4,
        '北向资金净买入': 1.3,
        '主力资金流入': 1.3,
        '金叉信号': 1.2,
        '突破阻力位': 1.2,
        '站上年线': 1.2,
        '牛市行情': 1.5,
        '政策利好': 1.3,
        '高送转预期': 1.2,

        # ----- 消极短语 -----
        '放量下跌': -1.5,
        '天量见顶': -1.4,
        '跌破支撑': -1.3,
        '断崖式下跌': -1.8,
        '业绩暴雷': -1.6,
        '业绩变脸': -1.5,
        '低于预期': -1.3,
        '北向资金净卖出': -1.3,
        '主力资金流出': -1.3,
        '死叉信号': -1.2,
        '跌破年线': -1.3,
        '熊市行情': -1.5,
        '监管处罚': -1.4,
        '立案调查': -1.5,
        '退市风险': -1.8,
        '债务违约': -1.6,
        '商誉减值': -1.3,
        '限售股解禁': -0.8,
        '大股东减持': -1.2,
        '股东清仓式减持': -1.5,
    }

    @classmethod
    def analyze_text(cls, text: str) -> Dict:
        """
        分析文本情感

        算法流程：
        1. 首先匹配金融短语（优先级最高）
        2. 匹配单词，考虑程度副词和否定词修饰
        3. 计算加权平均得分
        4. 归一化到 [-1, 1] 区间

        Args:
            text: 待分析的文本内容

        Returns:
            dict: 包含以下字段：
                - score: 情感得分 (-1 到 1)
                - label: 情感标签（非常积极/积极/中性/消极/非常消极）
                - level: 情感级别 (2, 1, 0, -1, -2)
                - positive_words: 匹配到的积极词汇列表
                - negative_words: 匹配到的消极词汇列表
                - phrases_matched: 匹配到的金融短语列表
        """
        if not text:
            return {
                'score': 0,
                'label': '中性',
                'level': SentimentLevel.NEUTRAL.value,
                'positive_words': [],
                'negative_words': [],
                'phrases_matched': []
            }

        text = text.lower()
        positive_found = []
        negative_found = []
        phrases_matched = []
        score = 0

        # =====================================================================
        # 第一步：匹配金融短语（短语优先级高于单词）
        # =====================================================================
        for phrase, phrase_score in cls.PHRASE_DICT.items():
            if phrase in text:
                phrases_matched.append(phrase)
                score += phrase_score
                # 从文本中移除已匹配的短语，避免重复计分
                text = text.replace(phrase, ' ')

        # =====================================================================
        # 第二步：检测积极词汇
        # =====================================================================
        for word in cls.POSITIVE_WORDS:
            if word in text:
                positive_found.append(word)
                word_score = 1.0

                # 检查词语前面的程度副词
                for degree_word, multiplier in cls.DEGREE_WORDS.items():
                    # 程度副词紧邻关键词 或 在关键词前5个字符内
                    word_pos = text.find(word)
                    if word_pos > 0:
                        prefix = text[max(0, word_pos - 5):word_pos]
                        if degree_word in prefix:
                            word_score *= multiplier
                            break

                # 检查否定词（否定词通常紧邻关键词）
                for neg in cls.NEGATION_WORDS:
                    if neg + word in text:
                        word_score *= -1  # 否定后变为相反极性
                        break

                score += word_score

        # =====================================================================
        # 第三步：检测消极词汇
        # =====================================================================
        for word in cls.NEGATIVE_WORDS:
            if word in text:
                negative_found.append(word)
                word_score = -1.0

                # 检查程度副词
                for degree_word, multiplier in cls.DEGREE_WORDS.items():
                    word_pos = text.find(word)
                    if word_pos > 0:
                        prefix = text[max(0, word_pos - 5):word_pos]
                        if degree_word in prefix:
                            word_score *= multiplier
                            break

                # 检查否定词（否定消极词变积极）
                for neg in cls.NEGATION_WORDS:
                    if neg + word in text:
                        word_score *= -1
                        break

                score += word_score

        # =====================================================================
        # 第四步：得分归一化
        # =====================================================================
        total_matches = len(positive_found) + len(negative_found) + len(phrases_matched)
        if total_matches > 0:
            # 使用加权平均，避免词汇数量过多导致得分过于极端
            score = score / (total_matches ** 0.5)  # 使用平方根归一化
            score = max(-1, min(1, score))  # 限制在 [-1, 1]

        # =====================================================================
        # 第五步：确定情感标签和级别
        # =====================================================================
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
            'negative_words': list(set(negative_found)),
            'phrases_matched': phrases_matched
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
