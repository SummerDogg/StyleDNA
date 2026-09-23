#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
相似语料智能召回工具 (Context Retriever)

功能：
- 根据用户给定的本次写作主题、关键词或体裁，从 raw/ 语料库中检索匹配度最高的 Top-5 原文
- 结合 _meta/ 元数据标签（article_type, topic_tags）与正文 BM25 / 词频匹配
- 支持直接输出推荐列表或将 5 篇参考原文合并导出为 AI 写作提示上下文
"""

import os
import sys
import re
import json
import math
import argparse
from pathlib import Path
from collections import Counter

# 尝试导入 jieba
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False


def tokenize(text: str) -> list:
    """分词辅助函数"""
    text = re.sub(r'#|\*|`|\[|\]|\(|\)|!|<[^>]+>', ' ', text)
    if HAS_JIEBA:
        return [w.strip().lower() for w in jieba.cut(text) if len(w.strip()) > 1]
    else:
        words = re.findall(r'[a-zA-Z]{2,}|[\u4e00-\u9fa5]{2,3}', text.lower())
        return words


class SimpleBM25:
    """轻量级 BM25 检索算法实现"""
    def __init__(self, corpus_docs: list, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus_docs = corpus_docs
        self.doc_lengths = [len(doc) for doc in corpus_docs]
        self.avg_doc_len = (sum(self.doc_lengths) / len(self.doc_lengths)) if self.doc_lengths else 1
        self.doc_count = len(corpus_docs)
        self.df = Counter()
        self.doc_freqs = []

        for doc in corpus_docs:
            freq = Counter(doc)
            self.doc_freqs.append(freq)
            for term in freq.keys():
                self.df[term] += 1

        self.idf = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens: list) -> list:
        scores = []
        for idx, doc_freq in enumerate(self.doc_freqs):
            doc_len = self.doc_lengths[idx]
            score = 0.0
            for term in query_tokens:
                if term not in doc_freq:
                    continue
                tf = doc_freq[term]
                idf = self.idf.get(term, 0.1)
                num = tf * (self.k1 + 1)
                denom = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (num / denom)
            scores.append(score)
        return scores


def load_author_corpus(base_dir: str):
    base_path = Path(base_dir)
    raw_dir = base_path / "raw"
    if not raw_dir.exists():
        raw_dir = base_path / "raw-corpus"
    if not raw_dir.exists():
        raw_dir = base_path

    meta_dir = base_path / "_meta"

    articles = []
    for f in list(raw_dir.glob("*.md")) + list(raw_dir.glob("*.txt")):
        filename = f.name
        content = f.read_text(encoding="utf-8", errors="ignore")
        
        # 尝试读取同名或对应的 meta 文件
        meta = {}
        if meta_dir.exists():
            meta_json = meta_dir / f"{f.stem}.json"
            meta_md = meta_dir / f"{f.stem}.md"
            if meta_json.exists():
                try:
                    meta = json.loads(meta_json.read_text(encoding="utf-8"))
                except Exception:
                    pass
            elif meta_md.exists():
                pass

        # 解析文件名中的日期前缀 (例如 2024-05-01)
        date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', filename)
        article_date = date_match.group(1) if date_match else "0000-00-00"

        articles.append({
            "path": str(f),
            "filename": filename,
            "title": meta.get("title", f.stem),
            "date": meta.get("date", article_date),
            "article_type": meta.get("article_type", ""),
            "topic_tags": meta.get("topic_tags", []),
            "content": content
        })

    return articles


def search_similar_articles(author_dir: str, query: str, top_k: int = 5, article_type: str = ""):
    articles = load_author_corpus(author_dir)
    if not articles:
        raise ValueError(f"在 {author_dir} 中未找到可用文章语料")

    query_tokens = tokenize(query)
    
    # 建立分词文档
    tokenized_docs = []
    for a in articles:
        # 给标题和标签增加加权
        extra_tokens = tokenize(a["title"]) * 3 + tokenize(" ".join(a["topic_tags"])) * 2
        body_tokens = tokenize(a["content"][:3000])  # 前 3000 字作为主要考量
        tokenized_docs.append(extra_tokens + body_tokens)

    bm25 = SimpleBM25(tokenized_docs)
    scores = bm25.get_scores(query_tokens)

    # 综合体裁过滤与时间加权
    ranked = []
    for idx, art in enumerate(articles):
        score = scores[idx]
        
        # 若指定了体裁且匹配，给予加分
        if article_type and article_type.lower() in (art["article_type"].lower() + " " + art["filename"].lower()):
            score += 2.0
            
        ranked.append({
            "article": art,
            "score": score
        })

    # 排序：相关度优先，相同相关度下按日期倒序
    ranked.sort(key=lambda x: (x["score"], x["article"]["date"]), reverse=True)
    return ranked[:top_k]


def main():
    parser = argparse.ArgumentParser(description="相似语料智能召回工具")
    parser.add_argument("author_dir", help="目标作者或账号根目录 (包含 raw/ 和 _meta/)")
    parser.add_argument("-q", "--query", required=True, help="本次写作的主题、大纲或关键词")
    parser.add_argument("-t", "--type", default="", help="可选：指定文章体裁 (如: 访谈 / 深度分析 / 短评)")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="召回文章数量 (默认: 5)")
    parser.add_argument("--export-context", help="将选中的参考原文合并导出为指定的 Markdown 文件")

    args = parser.parse_args()

    try:
        results = search_similar_articles(
            author_dir=args.author_dir,
            query=args.query,
            top_k=args.top_k,
            article_type=args.type
        )
    except Exception as e:
        print(f"检索失败: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n为您检索到与 [{args.query}] 最匹配的 Top-{len(results)} 篇参考原文：\n")
    print(f"{'序号':<4} | {'相关分':<7} | {'日期':<10} | {'体裁/标签':<15} | {'文件名/标题'}")
    print("-" * 75)

    exported_chunks = []
    for idx, item in enumerate(results, 1):
        art = item["article"]
        tags_str = art["article_type"] or ",".join(art["topic_tags"][:2]) or "-"
        print(f"{idx:<4} | {item['score']:<7.2f} | {art['date']:<10} | {tags_str:<15} | {art['filename']}")
        
        if args.export_context:
            exported_chunks.append(f"# 参考样本 {idx}：{art['filename']}\n\n{art['content']}\n\n---\n")

    if args.export_context:
        Path(args.export_context).write_text("\n".join(exported_chunks), encoding="utf-8")
        print(f"\n已将 5 篇参考原文合并导出至: {args.export_context}")


if __name__ == "__main__":
    main()
