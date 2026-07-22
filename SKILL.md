---
name: mingli-skill
description: 基于可审计历法数据的八字、紫微斗数、流年与大运工具。当用户询问命盘、八字、紫微、流年、大运、事业、财运、关系、性格或传统命理文化时使用。
---

# MingLi Skill

本 Skill 将历法计算、结构化信号和传统文化解释分开。四柱、节气、大运和紫微宫位是可回归验证的数据；传统解释只能作为文化参考，不能被描述为对现实结果或未来事件的证明。

完整项目说明见 [README.md](./README.md)，使用边界见 [ETHICS.md](./ETHICS.md)，方法约定见 [docs/methodology.md](./docs/methodology.md)。

## 输入

优先收集：

1. 公历出生日期与时分秒。
2. 性别。
3. 出生地或经纬度与时区。
4. 出生时间误差范围。
5. 需要分析的明确日期区间。

`birth_context` 存在时默认使用真太阳时。未提供地点的兼容调用按标准时间排盘，并会返回 `time_correction_unavailable` 警告。

23:00 至 00:59 的紫微子时口径可通过 `birth_context.zi_hour_convention` 明确：

- `benchmark`：兼容旧行为，23:00 为晚子、00:00 为早子。
- `early`：明确按早子时。
- `late`：明确按晚子时。

该约定属于命盘审计输入，会写入 `birth_time` 和 `chart_id`。

## 基础调用

```python
import json
from tools import HybridMingliToolkit

toolkit = HybridMingliToolkit()
birth_fields = {
    "year": "<出生年份>",
    "month": "<出生月份>",
    "day": "<出生日期>",
    "hour": "<出生小时>",
    "minute": "<出生分钟>",
    "gender": "<性别>",
}
birth_context = {
    "place": {
        "name": "<城市、县或地区名称>",
        "country_code": "<ISO 3166-1 国家代码>",
    },
    "uncertainty_minutes": "<时间误差分钟数>",
}
analysis_period = {
    "start": "<YYYY-MM-DD>",
    "end": "<YYYY-MM-DD>",
    "granularity": "<year|month|day>",
}

# 将运行时收集的字段传入；Skill 文档不保存个人出生资料。
result = json.loads(toolkit.analyze_question(
    **birth_fields,
    category="<分析类别>",
    question="<分析问题>",
    options_json="[]",
    birth_context=birth_context,
    analysis_period=analysis_period,
))
```

检查 `component_status`、`data_quality_warnings`、`birth_time` 与 `chart_id`，再阅读结构化字段。不要只根据单一标签生成确定性结论。

## 输出层次

1. **历法层**：`bazi.四柱`、`bazi.大运`、`liunian`、`birth_time`。
2. **结构层**：`strength_assessment`、十神、五行、`ziwei_raw`。
3. **解释层**：`career_analysis`、`wealth_analysis`、`marriage_analysis` 等传统文化推演。

`ziwei_raw` 包含十二宫、星曜亮度、生年四化、十年大限及 `紫微审计`；`ziwei` 只是兼容摘要。紫微精确后端不可用时，`component_status.ziwei` 会标记为 `degraded`，近似盘不能作为完整紫微规则或回归依据。

## 流年与流月

具体事件必须传 `analysis_period`。流年以立春边界切分，流月以十二个节气边界切分。仅从问题文本解析年份是降级模式，必须保留其质量提示。

## 规则证据

读取旺衰、喜用和忌神时，只使用 `strength_assessment`：

- `seasonal-strength-v2` 给出月令、五行得分、日主占比、阈值和旺衰结论。
- `element-balance-v1` 从同一旺衰结论派生喜用神、喜神和忌神。
- `legacy_strength`、`legacy_preference` 及基础命盘中的旧喜忌字段只供兼容比对，不能用来生成解释。

若 `strength_assessment.conflicts` 非空，依赖旺衰或喜用的模板结论必须降级为待定，并在解释中列出冲突。流年和大运必须读取 `喜忌信号`：`direct_yong`/`direct_ji` 是直接命中，`supports_yong`/`supports_ji` 是生扶关系；两者都只是传统结构信号，不是对吉凶或现实事件的断言。

## 可选知识引用

仅在需要传统术语、方法论或书目线索时传入 `knowledge_query` 或 `knowledge_packs`。知识检索只读取通过 SHA-256 校验的本地 Markdown，返回包版本、来源、文件、章节和行号；不访问网络，也不参与排盘计算。

## 可选解释文本

解释文本必须与排盘分离。先读取 `interpretation_brief`，再提供 `interpretation_document`：

```python
interpretation_document = {
    "schema_version": "interpretation-v1",
    "chart_id": result["chart_id"],
    "sections": [{
        "id": "career",
        "title": "事业节奏",
        "body": "传统文化解释文本。",
        "evidence_ids": ["career_analysis", "ziwei.palaces"],
        "uncertainty": "仍需结合行业、岗位和实际业绩验证。",
    }],
}
```

每段必须引用允许的证据 ID 并说明不确定性。报告会对文本进行 HTML 转义。该契约只验证来源与字段边界，不验证或提升预测准确率。

## 规则建议

`rules_suggestion` 只服务于低风险的多选题兼容场景。没有选项时它会返回 `rules_suggestion_no_options`，不会随机选择答案。健康、伤害、法律，以及涉及死亡、医疗、投资、借贷、赌博、破产、怀孕或离婚等高风险内容时会被明确抑制，不生成规则选项预测。

## 报告

需要单文件报告时调用 `generate_html_report`。报告包含命盘标识、校时、四柱、大运、流年流月、紫微十二宫、质量状态、知识引用和免责声明。只有明确传入 `output_path` 时才写入文件。

## 验证与数据

```bash
python3 -m unittest discover -v
bash -n setup.sh
```

外部数据集仅通过 `datasets/manifest.json` 和 `scripts/` 中的导入、验证工具接入。不要提交个人出生资料、命盘报告、临时基准样本或机器相关绝对路径。
