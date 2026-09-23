#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图文排版与视觉特征分析工具 (L6 视觉风格分析)

功能：
- 统计配图密度与图文间距（平均间隔段落数、每千字图片数）
- 分析排版标记分布（标题层级 H1-H4、引用块、代码块、分割线、无序/有序列表）
- 提取图片说明文本（alt text）与图文协作倾向
- 自动生成符合 视觉风格指南.md 规范的分析报告
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import Counter


def analyze_visual_style(corpus_dir: str) -> dict:
    target_path = Path(corpus_dir)
    if not target_path.exists():
        raise FileNotFoundError(f"指定的语料路径不存在: {corpus_dir}")

    files = []
    if target_path.is_file():
        files = [target_path]
    else:
        for ext in ("*.md", "*.txt", "*.html"):
            files.extend(list(target_path.glob(ext)))

    if not files:
        raise ValueError(f"在 {corpus_dir} 中未找到任何可分析文件")

    total_articles = len(files)
    total_images = 0
    total_chars = 0
    articles_with_cover = 0
    image_intervals = []  # 连续图片之间的段落数间隔
    
    heading_counter = Counter()
    blockquote_count = 0
    codeblock_count = 0
    hr_count = 0
    list_item_count = 0
    alt_texts = []

    for f in files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        chars = len(re.sub(r'\s+', '', content))
        total_chars += chars
        
        # 1. 提取图片（Markdown 格式与 HTML <img> 标签）
        md_images = re.findall(r'!\[(.*?)\]\((.*?)\)', content)
        html_images = re.findall(r'<img[^>]+src=["\'](.*?)["\']', content)
        
        article_img_count = len(md_images) + len(html_images)
        total_images += article_img_count
        
        for alt, _ in md_images:
            if alt.strip():
                alt_texts.append(alt.strip())
                
        # 检查是否第一部分就是图片（首图/封面图）
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if lines and (lines[0].startswith('![') or lines[0].startswith('<img')):
            articles_with_cover += 1

        # 2. 计算图文间隔（每隔多少个非空段落出现一张图）
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        current_gap = 0
        for p in paragraphs:
            if p.startswith('![') or p.startswith('<img') or '![' in p or '<img' in p:
                image_intervals.append(current_gap)
                current_gap = 0
            else:
                current_gap += 1
                
        # 3. 排版元素统计
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, flags=re.MULTILINE)
        for h_level, _ in headings:
            heading_counter[f"H{len(h_level)}"] += 1
            
        blockquotes = re.findall(r'^>\s+(.+)$', content, flags=re.MULTILINE)
        blockquote_count += len(blockquotes)
        
        codeblocks = re.findall(r'```[\s\S]*?```', content)
        codeblock_count += len(codeblocks)
        
        hrs = re.findall(r'^(\-{3,}|\*{3,}|_{3,})$', content, flags=re.MULTILINE)
        hr_count += len(hrs)
        
        lists = re.findall(r'^\s*([-*+]|\d+\.)\s+(.+)$', content, flags=re.MULTILINE)
        list_item_count += len(lists)

    # 计算均值与比率
    avg_images_per_article = total_images / total_articles if total_articles else 0
    img_density_per_thousand = (total_images / (total_chars / 1000.0)) if total_chars else 0
    avg_interval_paras = (sum(image_intervals) / len(image_intervals)) if image_intervals else 0
    cover_ratio = (articles_with_cover / total_articles) * 100 if total_articles else 0

    return {
        "total_articles": total_articles,
        "total_images": total_images,
        "avg_images_per_article": round(avg_images_per_article, 1),
        "img_density_per_thousand": round(img_density_per_thousand, 2),
        "avg_interval_paragraphs": round(avg_interval_paras, 1),
        "cover_image_ratio": round(cover_ratio, 1),
        "heading_distribution": dict(heading_counter),
        "layout_elements": {
            "blockquote_count": blockquote_count,
            "codeblock_count": codeblock_count,
            "hr_count": hr_count,
            "list_item_count": list_item_count,
        },
        "sample_alt_texts": alt_texts[:10]
    }


def generate_visual_report(stats: dict) -> str:
    md = []
    md.append("# 视觉风格与排版指南 (自动统计分析)")
    md.append("")
    md.append(f"> 统计基数：共分析 {stats['total_articles']} 篇文章，发现配图 {stats['total_images']} 张。")
    md.append("")
    md.append("## 1. 配图节奏与密度")
    md.append(f"- **篇均配图数量**：{stats['avg_images_per_article']} 张/篇")
    md.append(f"- **配图密度**：平均每千字出现 {stats['img_density_per_thousand']} 张图")
    md.append(f"- **图文间距**：平均每隔 {stats['avg_interval_paragraphs']} 个段落出现一张图")
    md.append(f"- **首图/封面图出现率**：{stats['cover_image_ratio']}%")
    md.append("")
    md.append("## 2. 标题层级与排版架构")
    md.append("- **标题分布**：")
    for h, cnt in sorted(stats['heading_distribution'].items()):
        md.append(f"  - {h} 标题：{cnt} 次")
    md.append("")
    md.append("## 3. 结构化排版组件偏好")
    md.append(f"- **引用块 (Blockquote)**：共出现 {stats['layout_elements']['blockquote_count']} 处")
    md.append(f"- **代码块 (Codeblock)**：共出现 {stats['layout_elements']['codeblock_count']} 处")
    md.append(f"- **分割线 (HR)**：共出现 {stats['layout_elements']['hr_count']} 处")
    md.append(f"- **列表项 (List Item)**：共出现 {stats['layout_elements']['list_item_count']} 项")
    md.append("")
    
    if stats['sample_alt_texts']:
        md.append("## 4. 配图功能与图注采样 (Alt Text)")
        for alt in stats['sample_alt_texts']:
            md.append(f"- {alt}")
        md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="视觉风格与排版特征分析工具")
    parser.add_argument("corpus_path", help="语料目录路径或文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    args = parser.parse_args()

    try:
        stats = analyze_visual_style(args.corpus_path)
    except Exception as e:
        print(f"分析失败: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        output_content = json.dumps(stats, ensure_ascii=False, indent=2)
    else:
        output_content = generate_visual_report(stats)

    if args.output:
        Path(args.output).write_text(output_content, encoding="utf-8")
        print(f"排版与视觉分析完成，已写入: {args.output}")
    else:
        print(output_content)


if __name__ == "__main__":
    main()
