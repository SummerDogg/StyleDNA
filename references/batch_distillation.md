# 海量语料分批蒸馏与增量更新指南 (Batch & Incremental Distillation)

当目标作者或账号的文章数量较多（例如 20 篇以上、单篇字数较长）时，如果将全部文章一次性输入给大模型，容易发生**上下文长度超限**或**注意力衰减（Lost in the Middle）**。

建议采用 Map-Reduce 架构进行分批蒸馏与增量更新。

---

## 一、Map 阶段：单篇/小批次元数据与特征提取

将文章按 3-5 篇一组划分批次，并行或分步提取局部特征并存入 `_meta/` 目录。

### 单篇元数据结构 (`_meta/{文章文件名}.json`)

```json
{
  "title": "文章标题",
  "date": "YYYY-MM-DD",
  "author": "作者姓名",
  "article_type": "深度分析 | 访谈 | 短评 | 综述",
  "topic_tags": ["AI", "产品设计", "商业模式"],
  "hook_type": "场景式引入",
  "structure_summary": "冲突提出 -> 案例剖析 -> 底层逻辑 -> 开放式反思",
  "core_claims": ["核心命题1", "核心命题2"],
  "source_preference": ["一手访谈", "论文引用"]
}
```

---

## 二、Reduce 阶段：统计聚合与高阶规律提炼

### 1. 运行自动化统计工具（L1 与 L6）
执行脚本直接汇总整体语料数据：

```bash
# 自动生成语言统计报表
python3 scripts/analyze_corpus.py raw/ -o 语言DNA.md

# 自动生成视觉排版统计报表
python3 scripts/analyze_visual.py raw/ -o 视觉风格指南.md
```

### 2. 汇聚高阶规律（L2 - L5）
向模型输入聚合后的 `_meta/` 所有 JSON 文件及统计报表，要求模型：
- 归纳出现频次最高的 3 种结构模板 -> 形成 `文章结构模板.md`
- 提炼反复出现的全局核心假设与选题边界 -> 形成 `写作视角与认知框架.md`
- 组装成最终的 `Writing-DNA.md`

---

## 三、增量更新机制（Incremental Update）

当作者发布了新的 3-5 篇文章时，无需重新跑全量流程：

1. 将新文章存入 `raw/` 目录，并为新文章生成 `_meta/` 记录。
2. 重新运行 `scripts/analyze_corpus.py raw/` 刷新 L1 统计基准。
3. 检查新文章是否包含新的选题类型或结构形式，增量补充到 `文章结构模板.md` 和 `写作视角与认知框架.md`。
