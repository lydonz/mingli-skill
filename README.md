# MingLi Skill

面向 LLM Agent 的中文命理工具集。项目提供八字、紫微斗数、流年与大运等排盘能力，以及可供 Agent 使用的结构化数据、规则证据和数据质量状态。

本项目参考 [dfytensor/MingLiSkill](https://github.com/dfytensor/MingLiSkill) 的项目结构与命理工具设计。
本项目内置的可选本地知识包参考
[pengyunzhaoisme1207-bit/bazi-ziwei-mingli-cn](https://github.com/pengyunzhaoisme1207-bit/bazi-ziwei-mingli-cn)
的公开方法论文档，并保留固定提交、MIT 许可证和文件校验信息。

项目将“历法计算”和“命理解读”分开处理：四柱、节气、大运日期和紫微宫位可通过回归测试验证；事业、财运、婚姻等解读属于传统命理规则推演，应作为文化参考，而非医学、投资、就业或其他重大决策的依据。

## 功能

- **八字排盘**：公历/农历转换、四柱、十神、五行、纳音、十二长生、空亡。
- **节气与大运**：按精确节气计算年柱、月柱、起运时间和大运切换日期。
- **真太阳时**：结构化出生地点输入支持城市名或经纬度；输出时区、经度校正、均时差、有效排盘时间和节气比较时标。
- **出生时间误差**：可传入误差分钟数；枚举区间内全部时辰、换日、节气和年界候选命盘。
- **紫微斗数**：通过 `iztro` 生成十二宫和主星数据。
- **紫微审计数据**：保留十二宫主星/辅星详情、亮度、生年四化、十年大限、子时约定和 `iztro` 时辰索引。
- **流年区间分析**：支持年、月、日粒度的 `analysis_period`；结果按所选年界规则切分民用日期与干支流年。
- **流月分段**：按小寒、立春、惊蛰等十二个节气输出流月干支、十神和当期大运。
- **可审计输出**：每份综合结果包含 `chart_id`、`birth_time`、`strength_assessment`、规则证据与各组件状态。
- **高风险门控**：规则选项建议只用于低风险多选兼容场景；健康、伤害、法律，以及死亡、医疗、投资、借贷等主题会显示抑制状态，而不生成选项预测。
- **本地知识引用**：可选检索经 SHA-256 校验的本地 Markdown 知识包，返回固定版本、文件、章节、行号和摘录；不访问网络。
- **HTML 报告**：可生成单文件、无外链、适合浏览器阅读和打印的报告；只有显式指定路径时才写入本地文件。
- **解读文本契约**：可选解释文本必须绑定当前 `chart_id`、引用结构化 `evidence_ids` 并说明不确定性；报告将其作为纯文本安全转义。
- **其他工具包**：六爻、梅花易数、奇门遁甲、大六壬、面相手相和风水基础工具。

## 历法与数据质量

公历出生信息是默认输入。未传入地点的兼容调用按标准时间排盘，并返回 `time_correction_unavailable` 警告。

传入 `birth_context` 时，默认采用真太阳时：

1. 使用固定版本的本地 GeoNames 城市数据解析地点。
2. 用历史时区确定标准子午线。
3. 结合经度差与 NOAA 均时差计算校正分钟数。
4. 所有八字、大运、紫微和衍生分析共享同一份 `ComputedChart` 与 `chart_id`。

`effective_time` 是用于日柱和时柱的当地有效太阳时；`calendar_time` 是将出生民用时刻换算到 `lunar-python` 节气后端时标后的时间，专用于年柱和月柱的节气边界比较。两者都会写入 `birth_time`，避免将海外本地时钟直接与中国历法后端时钟比较。

城市名存在歧义时，接口返回候选地点而不会自行猜测。需要提供 `country_code`、省市信息或直接传入经纬度。

## 命理规则与解释

排盘的历法规则和解释规则分开版本化。四柱以节气月、可选年界和明确的子时口径计算；`birth_time` 会记录有效太阳时和节气比较时标。所有八字、大运、流年及衍生分析共享同一 `ComputedChart` 与 `chart_id`，不会由各模块按小时重新排盘。

当前旺衰规则为 `seasonal-strength-v2`。它以四柱干支及藏干的固定权重形成五行得分，并把月支与日主同类或生扶日主记为“得令”；日主五行占比大于 `0.35` 且得令为“身旺”，低于 `0.20` 为“身弱”，其余按得令分为“中和偏旺”或“中和偏弱”。每次输出都会在 `strength_assessment.evidence` 中给出月支、五行得分、比例、阈值和规则版本。

喜用规则为 `element-balance-v1`，只作为可复核的简化基线：

- 身旺或中和偏旺：用神取“我克”，喜神取“克我”，忌神取“同我”。
- 身弱或中和偏弱：用神取“生我”，喜神取“同我”，忌神取“我生”。

`strength_assessment` 是事业、财富和流年模块唯一读取的旺衰、喜用来源。旧排盘器的 `日主强弱`、`喜用神` 和 `legacy_strength` 仅为接口兼容保留；当旧值与当前规则不一致时，输出 `strength_model_conflict` 或 `preference_model_conflict`，依赖旺衰的确定性模板会降级为 `待定`。

流年和大运不会把“某五行直接命中喜用神”与“某五行生扶喜用神”混为一谈。`喜忌信号` 会逐项给出干支来源、五行和 `direct_yong`、`supports_yong`、`direct_ji` 或 `supports_ji` 等规则代码；它们是传统结构信号，不等于现实中的吉凶或事件预测。

## 安装

依赖 Python 3.10+、Node.js 和 npm。

```bash
python3 -m pip install -r requirements.txt
npm install
```

Python 依赖：

- `lunar-python`：节气、农历、四柱和起运日期。
- `geonamescache`：本地城市与时区数据。
- `pypinyin`：中文地名与 GeoNames 拼音别名匹配。
- `pyarrow`：可选的数据集导入与回归工具。

Node 依赖：

- `iztro`：紫微斗数排盘。

### 安装为 Skill

macOS / Linux 默认安装到 `~/.codex/skills/mingli-skill`：

```bash
bash ./setup.sh
```

也可以指定其他目标目录：

```bash
bash ./setup.sh ~/.agents/skills
```

Windows：

```cmd
setup.bat
```

## 快速开始

### 基础排盘

调用 `HybridMingliToolkit.analyze_question()` 时，提供出生年月日、时分、性别、分析类别、问题和 `options_json`。出生资料应由调用方在运行时传入；项目文档和示例不保存任何个人出生信息。

该兼容调用会按标准时间排盘，并在 `data_quality_warnings` 中说明没有地点校正。

### 真太阳时与具体日期分析

```python
birth_context = {
    "place": {
        "name": "<城市、县或地区名称>",
        "country_code": "<ISO 3166-1 国家代码>",
    },
    "uncertainty_minutes": "<出生时间误差分钟数>",
}

analysis_period = {
    "start": "<YYYY-MM-DD>",
    "end": "<YYYY-MM-DD>",
    "granularity": "<year|month|day>",
}
```

将这两个对象传入 `analyze_question()` 后，结果中的 `birth_time` 记录校时信息，`liunian.civil_to_bazi_year_segments` 按立春边界展示区间分段。

### 直接使用经纬度

```python
birth_context = {
    "place": {
        "name": "<地点名称>",
        "longitude": "<东经为正的十进制度数>",
        "latitude": "<北纬为正的十进制度数>",
        "timezone": "<IANA 时区>",
    },
    "time_basis": "true_solar",
}
```

`time_basis` 支持：

- `true_solar`：默认值，需要地点。
- `standard`：使用当地标准时间，不做真太阳时校正。

`birth_context.zi_hour_convention` 支持：

- `benchmark`：默认值，保持历史兼容行为，23:00 使用晚子时、00:00 使用早子时。
- `early`：23:00 至 00:59 明确按早子时传入紫微后端。
- `late`：23:00 至 00:59 明确按晚子时传入紫微后端。

该选择会写入 `birth_time`、紫微审计数据和 `chart_id`。即使四柱未变化，不同子时约定也不会共享同一个命盘标识。

`year_boundary` 支持 `lichun`（默认）和 `lunar_new_year`。该选择同时控制本命年柱、大运方向、流年、流月和日期区间切分；不得只对某一个模块单独切换。

### 紫微审计与十二宫报告

综合结果中的 `ziwei_raw` 保留 `iztro` 的十二宫结构化数据，而 `ziwei` 继续提供兼容摘要。每个宫位都可包含主星/辅星名称、亮度、生年四化、十二长生和十年大限；`紫微审计` 记录日历输入、子时约定、`iztro` 时辰索引和宫位数量。

HTML 报告会基于 `ziwei_raw` 生成固定 4x4 的十二宫视图。它只显示后端返回的结构化字段，不把传统解释伪装成排盘事实。

### 独立解读文本

排盘与解释文本分离。先取得分析结果的 `chart_id` 和 `interpretation_brief.allowed_evidence_ids`，再按契约传入解释文本：

```python
interpretation_document = {
    "schema_version": "interpretation-v1",
    "chart_id": result["chart_id"],
    "sections": [{
        "id": "career",
        "title": "事业节奏",
        "body": "传统命理解释文本。",
        "evidence_ids": ["career_analysis", "ziwei.palaces"],
        "uncertainty": "仍需结合行业、岗位和实际业绩验证。",
    }],
}
```

契约会拒绝不匹配的 `chart_id`、不存在的证据 ID、缺失的不确定性说明或无效字段。它不验证解释文本本身是否能预测未来；报告将标题和正文按纯文本转义。

### 本地知识库引用

知识包只用于补充传统命理的方法论、术语和阅读线索，不参与四柱、节气、紫微或大运计算。默认内置的
`bazi-ziwei-mingli-cn` 包固定到上游提交
`f086546f9d4ab0e6fd00f8c37364269241249115`，包含八字认识论、八字方法论、紫微概要和工具书索引。

只有显式传入 `knowledge_query` 或 `knowledge_packs` 才会检索，避免把与问题无关的文本混入分析：

```python
for reference in result["knowledge_references"]:
    print(reference["file"], reference["section"])
    print(reference["line_start"], reference["line_end"])
```

每次检索会先验证 `knowledge_packs/<pack-id>/manifest.json` 中列出的 SHA-256。缺少、损坏或版本不匹配的包不会静默使用，状态会显示在 `component_status.knowledge` 和 `knowledge_context.pack_statuses`。包的上游来源和许可见
[`knowledge_packs/bazi-ziwei-mingli-cn/UPSTREAM.md`](knowledge_packs/bazi-ziwei-mingli-cn/UPSTREAM.md)。

### 生成 HTML 报告

```python
report = json.loads(toolkit.generate_html_report(
    **birth_fields,
    category="<分析类别>",
    question="<分析问题>",
    birth_context=birth_context,
    analysis_period=analysis_period,
    title="<报告标题>",
    subject_name="<报告显示名称>",
    output_path="<输出 HTML 路径>",
))
```

返回结果中的 `html` 字段可直接交给浏览器或文件系统。报告不加载远程脚本、字体、图片或追踪服务。

## 综合结果结构

`HybridMingliToolkit.analyze_question()` 返回 JSON 字符串。主要字段：

| 字段 | 含义 |
|---|---|
| `chart_id` | 由有效太阳时、节气比较时标、性别、年界规则和时间口径生成的命盘标识。 |
| `birth_time` | 民用出生时间、有效太阳时、节气比较时标、地点、时区、校正分钟数、误差范围和全部候选命盘。 |
| `bazi` | 四柱、日主、十神、五行、喜忌、大运等基础数据。 |
| `ziwei` | 命宫、官禄、财帛、夫妻等宫位主星摘要。 |
| `ziwei_raw` | 完整十二宫、星曜亮度、四化、大限、子时约定与紫微审计元数据。 |
| `strength_assessment` | 当前衍生分析使用的旺衰评估、证据和冲突标记。 |
| `career_analysis` | 官杀、印绶、食伤、财星等事业相关结构化信号与证据。 |
| `wealth_analysis` | 财星强度、位置和规则证据；存在模型冲突时抑制确定性模板。 |
| `liunian` | 显式日期区间或文本年份回退模式下的流年对比。 |
| `liunian.流月分段` | 在月/日粒度区间内，按十二个节气切分的流月、十神和大运。 |
| `component_status` | 每个组件的 `ok`、`degraded` 或 `error` 状态。 |
| `data_quality_warnings` | 缺失地点、后端降级等质量提示。 |
| `knowledge_references` | 显式请求本地知识库时返回的行级参考；包含知识包、固定版本、来源、文件、章节、行号和摘录。 |
| `knowledge_context` | 显式请求本地知识库时返回的查询文本、包校验状态和使用边界。 |
| `interpretation_brief` | 当前命盘允许引用的证据 ID 和解释文本契约约束。 |
| `interpretation` | 显式传入解释文本时的校验结果和安全规范化文本；校验失败不会丢弃命盘。 |

`legacy_strength` 仅用于旧接口兼容。新衍生分析以 `strength_assessment` 为唯一旺衰来源。

`knowledge_references` 是传统命理的方法论与文化语境参考，不是未来事件、财富、健康或职业结果的预测证据。

`rules_suggestion` 只处理低风险多选题兼容场景。未提供选项会返回 `rules_suggestion_no_options`；健康、伤害、法律，以及死亡、医疗、投资、借贷、赌博、破产、怀孕或离婚等内容会返回可见的抑制状态，不能据此生成选项预测。

## 外部排盘回归

项目登记了 [DestinyLinker/MingLi-Bench](https://github.com/DestinyLinker/MingLi-Bench)
的 MIT 许可固定提交 `b7433280fd86d7a7c27debbc47d0303c218f0bfd`。导入器只读取其中 32 份预先由 `iztro` 生成的命盘结构，用于四柱和紫微的可重复回归；不会导入或评分其 160 道历史事件题的题干、选项与答案。

```bash
git clone https://github.com/DestinyLinker/MingLi-Bench.git /tmp/MingLi-Bench
git -C /tmp/MingLi-Bench checkout b7433280fd86d7a7c27debbc47d0303c218f0bfd

python3 scripts/import_mingli_bench.py \
  --source-dir /tmp/MingLi-Bench \
  --output-dir /tmp/mingli-bench-validation \
  --purpose bazi_chart_regression

python3 scripts/evaluate_dataset_regressions.py \
  --source-id mingli-bench \
  --records /tmp/mingli-bench-validation/chart-fixtures.jsonl \
  --purpose bazi_chart_regression \
  --output /tmp/mingli-bench-validation/bazi-report.json

python3 scripts/evaluate_dataset_regressions.py \
  --source-id mingli-bench \
  --records /tmp/mingli-bench-validation/chart-fixtures.jsonl \
  --purpose ziwei_chart_regression \
  --output /tmp/mingli-bench-validation/ziwei-report.json
```

在上述固定提交和当前依赖版本下：紫微的农历日期、命身宫、五行局、生肖与十二宫主辅星结构为 32/32 一致；四柱的月、日、时柱为 32/32 一致，年柱为 31/32 一致。唯一差异发生在立春后、农历新年前：本项目遵循显式的立春换年规则，而上游 `iztro` 的 `chineseDate` 年柱仍使用农历年。紫微对照的双方都依赖 `iztro`，因此它验证的是适配层和输出结构没有漂移，并非独立的天文历法验证。该报告仅说明排盘字段的一致或差异，不构成对事业、财运、健康或其他事件的预测能力结论。

## 工具包

| 工具包 | 主要能力 |
|---|---|
| `HybridMingliToolkit` | 综合排盘、流年、结构化证据和组件状态。 |
| `BaziToolkit` | 八字、四柱、大运、流年、十神、冲合、财官印食伤分析；个人排盘入口支持 `birth_context` 并构建 `ComputedChart`。 |
| `ZiweiToolkit` | 紫微十二宫、命宫、官禄、财帛、夫妻和疾厄分析；个人排盘入口支持 `birth_context` 并消费 `ComputedChart`。 |
| `LiuYaoToolkit` | 六爻起卦。 |
| `MeiHuaToolkit` | 梅花易数。 |
| `QiMenToolkit` | 奇门遁甲。 |
| `LiuRenToolkit` | 大六壬。 |
| `KnowledgeToolkit` | 列出和检索本地、版本固定且经过完整性校验的知识包。 |
| `PhysiognomyToolkit` | 面相手相基础查询。 |
| `FengShuiToolkit` | 八宅等风水基础工具。 |

所有公开工具类可从 `tools` 导入：

```python
from tools import ALL_TOOLKITS, BaziToolkit, HybridMingliToolkit, ZiweiToolkit
```

## 项目结构

```text
mingli-skill/
├── SKILL.md                 # Agent 使用说明和命理推理规则
├── ETHICS.md                # 使用边界、隐私与高风险事项说明
├── docs/methodology.md      # 分析层次、流月和报告输出约定
├── agents/openai.yaml       # Agent 展示与默认调用元数据
├── setup.sh / setup.bat     # Skill 安装脚本
├── knowledge_packs/         # 本地、版本固定且已校验的参考资料
├── tools/
│   ├── birth_context.py     # 地点解析、时区和真太阳时
│   ├── calendar_engine.py   # 节气、干支、四柱和大运
│   ├── chart_assessment.py  # 统一旺衰评估
│   ├── hybrid_tools.py      # 综合入口
│   ├── interpretation_contract.py # 证据绑定的解释文本校验
│   ├── knowledge_tools.py   # 本地知识包校验、检索和行级引用
│   ├── liunian_analyzer.py  # 日期区间与流年分析
│   ├── report_renderer.py   # 单文件 HTML 报告渲染
│   ├── safety_policy.py     # 高风险规则建议门控
│   └── ziwei_tools.py       # 紫微斗数工具
├── engine/
│   └── run_tools_engine.py  # 规则引擎
├── scripts/                 # 数据集导入、验证与回归脚本
├── tests/                   # 历法、真太阳时、接口与数据治理测试
└── datasets/manifest.json   # 外部数据来源与允许用途声明
```

## 测试

运行全部回归测试：

```bash
python3 -m unittest discover -v
```

测试覆盖：

- 节气、农历、四柱和大运与 `lunar-python` 的对照。
- 紫微输入转换与 `iztro` 后端。
- 真太阳时的经度校正、跨时辰、跨日与出生时间误差。
- 海外时区节气边界、夏令时无效时间、农历年界在大运/流年/流月中的一致性。
- 误差区间内全部候选四柱，以及独立八字、紫微和综合入口的共享 `chart_id`。
- 城市名歧义、地点解析失败和组件失败的可见状态。
- 规则建议在空选项与高风险主题下的抑制状态。
- `iztro` 缺失时紫微近似回退的可见降级状态。
- 同一 `chart_id` 在八字、财富、事业和流年输出中的一致性。
- 立春前后的日期区间流年切分。
- 十二个节气边界的流月切分与流月干支。
- 单文件 HTML 报告的无外链与显式写入行为。
- 紫微十二宫审计字段、早晚子时约定与 `chart_id` 隔离。
- 解释文本的命盘绑定、证据引用、不确定性和 HTML 转义。
- 本地知识包的固定版本、许可证和 SHA-256 校验，以及无网络检索、无匹配和缺包状态。
- 数据集来源、不可用于未来事件准确率声明的治理规则。

项目不会分发个人出生资料、命盘报告、临时盲测样本或绑定个人机器绝对路径的脚本。外部数据集通过 `datasets/manifest.json` 和 `scripts/` 中的可移植导入、验证工具接入。

## 参考项目与数据来源

- 参考项目：[dfytensor/MingLiSkill](https://github.com/dfytensor/MingLiSkill)。
- [DestinyLinker/MingLi-Bench](https://github.com/DestinyLinker/MingLi-Bench/tree/b7433280fd86d7a7c27debbc47d0303c218f0bfd)：紫微排盘回归参考和选择题基准，MIT License。
- [pengyunzhaoisme1207-bit/bazi-ziwei-mingli-cn](https://github.com/pengyunzhaoisme1207-bit/bazi-ziwei-mingli-cn)：内置知识包固定于提交 `f086546f9d4ab0e6fd00f8c37364269241249115`，用于方法论、术语和书目引用，MIT License。
- `czuo03/bazi-calculate-rlvr`：四柱计算回归候选数据，CC-BY-4.0。
- `czuo03/bazi-reasoning-300` 与 `AmareshHebbar/bazi-sft`：隔离的推理/实现对照数据，不作为排盘真值或现实事件预测依据。

具体版本、许可证、允许用途和禁止用途见 [datasets/manifest.json](./datasets/manifest.json)。

MingLi-Bench 的选择题结果只能说明该题集上的选项匹配情况，不能据此宣称事业、财运、婚姻或其他未来事件可以被准确预测。

## 免责声明

本项目用于传统命理文化、历法计算和 Agent 工具研究。输出不构成医疗诊断、心理治疗、法律建议、投资建议、职业保证或其他专业意见。请勿将命理解读作为高风险或重大人生决策的唯一依据。
