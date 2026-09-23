#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
风格吻合度与质量量化评估工具 (Style Evaluator)

功能：
- 对比生成文章与 语言DNA.md / 语料库基准统计数据
- 计算句长、长短句比例、加粗密度、标点偏好等关键指标的吻合度得分
- 扫描文章中的典型 AI 味套话与八股句式
- 输出量化评分报告与定向改写建议
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import Counter

# 引用同目录统计函数
from analyze_corpus import split_sentences, clean_markdown

# 常见 AI 腔调/高风险模板词
AI_CLICHE_PATTERNS = [
    (r"不仅如此|总而言之|综上所述|显而易见|毋庸置疑", "空洞过渡套话"),
    (r"不仅仅是.*?更是一场", "夸大象征意义与双重修辞"),
    (r"值得注意的是|深入探讨|不可否认的是", "冗余填料短语"),
    (r"不是.*?而是.*?也不是.*?而是", "过度否定式排比"),
    (r"让我们拭目以待|未来可期|站在时代的风口", "老套煽情升华"),
    (r"一方面.*?另一方面.*?与此同时", "三段论机械式连接"),
]


def parse_dna_stats(dna_file_path: str) -> dict:
    """尝试从 语言DNA.md 中提取历史基准指标"""
    content = Path(dna_file_path).read_text(encoding="utf-8", errors="ignore")
    
    baseline = {}
    
    # 提取平均句长
    m = re.search(r'平均句长[^\d]*(\d+\.?\d*)', content)
    if m:
        baseline["avg_sentence_len"] = float(m.group(1))
        
    # 提取短句比例
    m = re.search(r'短句占比[^\d]*(\d+\.?\d*)%', content)
    if m:
        baseline["short_ratio"] = float(m.group(1))

    # 提取长句比例
    m = re.search(r'长句占比[^\d]*(\d+\.?\d*)%', content)
    if m:
        baseline["long_ratio"] = float(m.group(1))

    # 提取加粗密度
    m = re.search(r'加粗密度[^\d]*(\d+\.?\d*)', content)
    if m:
        baseline["bold_density"] = float(m.group(1))

    return baseline


def evaluate_article(article_text: str, baseline_stats: dict = None) -> dict:
    total_chars = len(clean_markdown(article_text))
    sentences = split_sentences(article_text)
    total_sentences = len(sentences) or 1
    
    sentence_lens = [len(s) for s in sentences]
    avg_len = sum(sentence_lens) / total_sentences
    short_count = sum(1 for l in sentence_lens if l <= 15)
    long_count = sum(1 for l in sentence_lens if l >= 50)
    
    short_ratio = (short_count / total_sentences) * 100
    long_ratio = (long_count / total_sentences) * 100

    bold_matches = re.findall(r'\*\*(.+?)\*\*', article_text)
    bold_density = (len(bold_matches) / (total_chars / 1000.0)) if total_chars > 0 else 0

    # AI 痕迹筛查
    ai_hits = []
    for pattern, reason in AI_CLICHE_PATTERNS:
        matches = re.findall(pattern, article_text)
        if matches:
            ai_hits.append({
                "pattern": pattern,
                "reason": reason,
                "count": len(matches),
                "samples": matches[:3]
            })

    # 计算吻合度评分 (基准 100 分)
    score = 100.0
    deductions = []

    if baseline_stats:
        # 句长偏离度惩罚
        if "avg_sentence_len" in baseline_stats:
            diff = abs(avg_len - baseline_stats["avg_sentence_len"])
            if diff > 10:
                loss = min(15.0, diff * 1.0)
                score -= loss
                deductions.append(f"平均句长 ({round(avg_len,1)}字) 与基准 ({baseline_stats['avg_sentence_len']}字) 偏离较大，扣 {round(loss,1)} 分")

        # 短句比例偏离惩罚
        if "short_ratio" in baseline_stats:
            diff = abs(short_ratio - baseline_stats["short_ratio"])
            if diff > 15:
                loss = min(10.0, diff * 0.5)
                score -= loss
                deductions.append(f"短句比例 ({round(short_ratio,1)}%) 与基准 ({baseline_stats['short_ratio']}%) 偏离，扣 {round(loss,1)} 分")

        # 加粗密度偏离惩罚
        if "bold_density" in baseline_stats:
            diff = abs(bold_density - baseline_stats["bold_density"])
            if diff > 3:
                loss = min(10.0, diff * 1.5)
                score -= loss
                deductions.append(f"加粗密度 ({round(bold_density,1)}次/千字) 与基准 ({baseline_stats['bold_density']}次/千字) 偏离，扣 {round(loss,1)} 分")

    # AI 套话扣分
    for hit in ai_hits:
        penalty = hit["count"] * 4.0
        score -= min(15.0, penalty)
        deductions.append(f"检测到 AI 套话 [{hit['reason']}] 共 {hit['count']} 处，扣 {penalty} 分")

    final_score = max(0.0, min(100.0, score))

    return {
        "score": round(final_score, 1),
        "total_chars": total_chars,
        "metrics": {
            "avg_sentence_len": round(avg_len, 1),
            "short_sentence_ratio": round(short_ratio, 1),
            "long_sentence_ratio": round(long_ratio, 1),
            "bold_density": round(bold_density, 2),
        },
        "baseline": baseline_stats or {},
        "deductions": deductions,
        "ai_hits": ai_hits
    }


def main():
    parser = argparse.ArgumentParser(description="文章风格吻合度评估工具")
    parser.add_argument("article_path", help="待评估的文章文件路径 (.md / .txt)")
    parser.add_argument("-d", "--dna-file", help="参考 语言DNA.md 文件路径（用于对比基准指标）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出评估结果")

    args = parser.parse_args()

    article_p = Path(args.article_path)
    if not article_p.exists():
        print(f"待评估文件不存在: {args.article_path}", file=sys.stderr)
        sys.exit(1)

    article_text = article_p.read_text(encoding="utf-8", errors="ignore")
    
    baseline = {}
    if args.dna_file and Path(args.dna_file).exists():
        baseline = parse_dna_stats(args.dna_file)

    report = evaluate_article(article_text, baseline)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print(f" 文章风格吻合度与质量评估报告: {article_p.name}")
    print("=" * 60)
    print(f"\n综合评分: {report['score']} / 100")
    print(f"文章字数: {report['total_chars']} 字\n")
    
    print("【关键指标对比】")
    m = report["metrics"]
    b = report["baseline"]
    print(f"- 平均句长: {m['avg_sentence_len']} 字 (基准: {b.get('avg_sentence_len', '无')})")
    print(f"- 短句占比 (≤15字): {m['short_sentence_ratio']}% (基准: {b.get('short_ratio', '无')}%)")
    print(f"- 长句占比 (≥50字): {m['long_sentence_ratio']}% (基准: {b.get('long_ratio', '无')}%)")
    print(f"- 加粗密度: {m['bold_density']} 次/千字 (基准: {b.get('bold_density', '无')})\n")

    if report["deductions"]:
        print("【扣分项与偏离说明】")
        for d in report["deductions"]:
            print(f"- {d}")
        print("")

    if report["ai_hits"]:
        print("【发现的潜在 AI 味句式】")
        for hit in report["ai_hits"]:
            print(f"- [{hit['reason']}] (频次: {hit['count']}) -> 命中示例: {hit['samples']}")
        print("")

    if report["score"] >= 80 and not report["ai_hits"]:
        print("结论：风格吻合度极高，节奏自然，无明显 AI 套话痕迹。")
    elif report["score"] >= 65:
        print("结论：风格基本达标，建议根据上述偏离项微调句式与排版。")
    else:
        print("结论：风格偏离较大或含有较多 AI 套路表达，建议重新参照蒸馏规则改写。")


if __name__ == "__main__":
    main()
