#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语料特征统计分析工具 (L1 表层语言分析)

功能：
- 统计词频（支持中文分词与英文单词统计）
- 统计句长特征（平均句长、短句占比、长句占比）
- 统计标点符号与格式偏好（破折号、括号、加粗密度等）
- 统计段落特征（段落长度、单句成段率）
- 自动生成符合 语言DNA.md 规范的 Markdown 统计报表
"""

import os
import sys
import re
import json
import argparse
from collections import Counter
from pathlib import Path

# 尝试导入 jieba，若不存在则使用基础正则分词回退机制
try:
    import jieba
    import jieba.posseg as pseg
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# 中文常见停用词列表（轻量级内置）
DEFAULT_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "他", "她", "它", "们", "而", "及", "与", "或", "等", "但",
    "因为", "所以", "如果", "虽然", "我们", "你们", "他们", "之", "为", "以", "所",
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "it", "this",
    "that", "i", "you", "he", "she", "we", "they"
}


def clean_markdown(text: str) -> str:
    """清理 Markdown 中的代码块、链接地址等干扰字符"""
    # 移除代码块
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*?`', '', text)
    # 移除图片链接但保留 alt 说明
    text = re.sub(r'!\[(.*?)\]\([^)]*\)', r'\1', text)
    # 移除普通链接 URL 保留文本
    text = re.sub(r'\[(.*?)\]\([^)]*\)', r'\1', text)
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    return text


def split_sentences(text: str) -> list:
    """分句函数，支持中英文常见终止符"""
    # 按换行和句子终止符切分
    raw_sentences = re.split(r'([。！？!?\n]+)', text)
    sentences = []
    for i in range(0, len(raw_sentences) - 1, 2):
        s = raw_sentences[i].strip() + raw_sentences[i+1].strip()
        s = s.replace('\n', ' ').strip()
        if len(s) > 1:
            sentences.append(s)
    if len(raw_sentences) % 2 == 1 and raw_sentences[-1].strip():
        s = raw_sentences[-1].strip().replace('\n', ' ')
        if len(s) > 1:
            sentences.append(s)
    return sentences


def analyze_corpus(corpus_dir: str) -> dict:
    """分析语料目录中的所有文章"""
    target_path = Path(corpus_dir)
    if not target_path.exists():
        raise FileNotFoundError(f"指定的语料路径不存在: {corpus_dir}")

    files = []
    if target_path.is_file():
        files = [target_path]
    else:
        for ext in ("*.md", "*.txt"):
            files.extend(list(target_path.glob(ext)))

    if not files:
        raise ValueError(f"在 {corpus_dir} 中未找到任何 .md 或 .txt 文件")

    total_chars = 0
    all_text = []
    raw_texts = []
    
    # 标点符号与格式统计计数器
    punct_counter = Counter()
    bold_count = 0
    heading_count = 0
    heading_lengths = []
    
    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        raw_texts.append(content)
        
        # 统计加粗出现次数
        bold_matches = re.findall(r'\*\*(.+?)\*\*', content)
        bold_count += len(bold_matches)
        
        # 统计标题
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, flags=re.MULTILINE)
        heading_count += len(headings)
        for h in headings:
            heading_lengths.append(len(h[1].strip()))
            
        cleaned = clean_markdown(content)
        all_text.append(cleaned)
        total_chars += len(cleaned)
        
        # 标点符号统计
        punct_counter["破折号（——或--）"] += len(re.findall(r'——|--', content))
        punct_counter["括号（()或（））"] += len(re.findall(r'[（）\(\)]', content)) // 2
        punct_counter["冒号（:或：）"] += len(re.findall(r'[:：]', content))
        punct_counter["省略号（……或...）"] += len(re.findall(r'……|\.{3,}', content))
        punct_counter["问号（?或？）"] += len(re.findall(r'[?？]', content))
        punct_counter["感叹号（!或！）"] += len(re.findall(r'[!！]', content))
        punct_counter["双引号（“”或\"\"）"] += len(re.findall(r'[“”"]', content)) // 2

    combined_text = "\n".join(all_text)
    
    # 1. 句长分析
    sentences = split_sentences(combined_text)
    sentence_lengths = [len(s) for s in sentences if len(s) > 0]
    total_sentences = len(sentence_lengths) or 1
    
    avg_sentence_len = sum(sentence_lengths) / total_sentences
    short_sentences = sum(1 for length in sentence_lengths if length <= 15)
    long_sentences = sum(1 for length in sentence_lengths if length >= 50)
    
    short_ratio = (short_sentences / total_sentences) * 100
    long_ratio = (long_sentences / total_sentences) * 100

    # 2. 段落分析
    paragraphs = [p.strip() for p in combined_text.split('\n') if len(p.strip()) > 0]
    total_paragraphs = len(paragraphs) or 1
    avg_para_len = total_chars / total_paragraphs
    avg_para_sentences = total_sentences / total_paragraphs

    # 3. 词频分析
    words_counter = Counter()
    nouns_counter = Counter()
    verbs_counter = Counter()
    adverbs_counter = Counter()

    if HAS_JIEBA:
        for text in all_text:
            words = pseg.cut(text)
            for w, flag in words:
                w_str = w.strip()
                if len(w_str) <= 1 or w_str.lower() in DEFAULT_STOPWORDS:
                    continue
                words_counter[w_str] += 1
                if flag.startswith('n'):
                    nouns_counter[w_str] += 1
                elif flag.startswith('v'):
                    verbs_counter[w_str] += 1
                elif flag.startswith('d'):
                    adverbs_counter[w_str] += 1
    else:
        # 回退分词（中文 2-4 字符词及英文单词）
        for text in all_text:
            en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
            for ew in en_words:
                if ew not in DEFAULT_STOPWORDS:
                    words_counter[ew] += 1
            # 基础中文词频提取
            zh_chars = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
            for zw in zh_chars:
                if zw not in DEFAULT_STOPWORDS:
                    words_counter[zw] += 1

    bold_density = (bold_count / (total_chars / 1000.0)) if total_chars > 0 else 0
    avg_heading_len = (sum(heading_lengths) / len(heading_lengths)) if heading_lengths else 0

    return {
        "article_count": len(files),
        "total_chars": total_chars,
        "total_sentences": total_sentences,
        "total_paragraphs": total_paragraphs,
        "sentence_stats": {
            "avg_length": round(avg_sentence_len, 1),
            "short_sentence_ratio": round(short_ratio, 1),
            "long_sentence_ratio": round(long_ratio, 1),
        },
        "paragraph_stats": {
            "avg_chars": round(avg_para_len, 1),
            "avg_sentences": round(avg_para_sentences, 1),
        },
        "punctuation_stats": dict(punct_counter),
        "formatting_stats": {
            "bold_count": bold_count,
            "bold_density_per_thousand": round(bold_density, 2),
            "heading_count": heading_count,
            "avg_heading_len": round(avg_heading_len, 1),
        },
        "top_words": words_counter.most_common(50),
        "top_nouns": nouns_counter.most_common(30) if HAS_JIEBA else [],
        "top_verbs": verbs_counter.most_common(20) if HAS_JIEBA else [],
        "top_adverbs": adverbs_counter.most_common(15) if HAS_JIEBA else [],
    }


def generate_markdown_report(stats: dict) -> str:
    """根据分析结果生成规范的 Markdown 报告片段"""
    md = []
    md.append("# 语言DNA (自动统计分析)")
    md.append("")
    md.append(f"> 样本总量：共分析 {stats['article_count']} 篇文章，总计约 {stats['total_chars']} 字。")
    md.append("")
    md.append("## 1. 句式与节奏特征")
    md.append(f"- **平均句长**：{stats['sentence_stats']['avg_length']} 字")
    md.append(f"- **短句占比 (≤15字)**：{stats['sentence_stats']['short_sentence_ratio']}%")
    md.append(f"- **长句占比 (≥50字)**：{stats['sentence_stats']['long_sentence_ratio']}%")
    md.append(f"- **段落平均长度**：{stats['paragraph_stats']['avg_chars']} 字 (约 {stats['paragraph_stats']['avg_sentences']} 句/段)")
    md.append("")
    md.append("## 2. 标点与格式偏好")
    md.append(f"- **加粗密度**：平均每千字加粗 {stats['formatting_stats']['bold_density_per_thousand']} 次 (总计 {stats['formatting_stats']['bold_count']} 处)")
    md.append(f"- **小标题平均字数**：{stats['formatting_stats']['avg_heading_len']} 字 (共 {stats['formatting_stats']['heading_count']} 个标题)")
    md.append("- **核心标点使用分布**：")
    for k, v in stats['punctuation_stats'].items():
        md.append(f"  - {k}：{v} 次")
    md.append("")
    md.append("## 3. 高频词汇分析")
    
    if stats['top_nouns']:
        md.append("### 3.1 核心高频名词 (Top 20)")
        noun_list = [f"{w} ({c})" for w, c in stats['top_nouns'][:20]]
        md.append("、".join(noun_list))
        md.append("")
        
    if stats['top_verbs']:
        md.append("### 3.2 常用动词 (Top 15)")
        verb_list = [f"{w} ({c})" for w, c in stats['top_verbs'][:15]]
        md.append("、".join(verb_list))
        md.append("")

    if stats['top_adverbs']:
        md.append("### 3.3 高频副词/修饰词 (Top 10)")
        adv_list = [f"{w} ({c})" for w, c in stats['top_adverbs'][:10]]
        md.append("、".join(adv_list))
        md.append("")

    if not stats['top_nouns']:
        md.append("### 3.1 高频核心词汇 (Top 30)")
        word_list = [f"{w} ({c})" for w, c in stats['top_words'][:30]]
        md.append("、".join(word_list))
        md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="语料特征统计分析工具")
    parser.add_argument("corpus_path", help="语料目录路径或单个文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出至 stdout）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    
    args = parser.parse_args()
    
    try:
        stats = analyze_corpus(args.corpus_path)
    except Exception as e:
        print(f"分析失败: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output_content = json.dumps(stats, ensure_ascii=False, indent=2)
    else:
        output_content = generate_markdown_report(stats)

    if args.output:
        Path(args.output).write_text(output_content, encoding="utf-8")
        print(f"统计分析完成，已写入: {args.output}")
    else:
        print(output_content)


if __name__ == "__main__":
    main()
