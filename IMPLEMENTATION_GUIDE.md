# 🎯 完整项目框架总结与实现路线图

## 核心架构确认

```
                    ┌─────────────────────────────────────┐
                    │  运行入口: run_compliance_check.py  │
                    │  命令: python run_compliance_check.py│
                    │        --input trades.json           │
                    │        --regimes CFTC,EMIR          │
                    └──────────┬──────────────────────────┘
                               │
                   ┌───────────┼───────────┐
                   ▼           ▼           ▼
            ┌────────────┐ ┌────────────┐ ┌────────────┐
            │ Module 1   │ │ Module 2   │ │ Module 3   │
            │  Parser    │ │   UPI      │ │ Compliance │
            │            │ │  Lookup    │ │  Checker   │
            └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
                  │              │              │
         parsed_trades.json  upi_lookup.json compliance_report.json
                  │              │              │
                  └──────────────┬──────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Module 5: Dashboard   │
                    │  (Streamlit)           │
                    │  - 4 可视化            │
                    │  - 书面解读 (2-3段)   │
                    │  - 交互式图表          │
                    └────────────────────────┘
```

---

## 📌 现状与待完成

### ✅ 已完成
- [x] **run_compliance_check.py** - 主程序CLI入口
  - ✓ 参数解析 (--input, --regimes, --library, --no-dashboard)
  - ✓ 三模块编排
  - ✓ 进度输出
  - ✓ Streamlit启动

- [x] **src/module2_upi_lookup.py** - UPI引擎（含启发式匹配）
  - ✓ 两层匹配策略
  - ✓ Token相似度算法
  - ✓ Codeset缓存
  - ✓ LIBOR弃用检测
  - ✓ Mock UPI代码生成

- [x] **src/dashboard.py** - Streamlit可视化
  - ✓ 热力图 (28×2矩阵)
  - ✓ 字段失败频率图
  - ✓ 资产类别分解图
  - ✓ 分类边界面板 (T026-T028)
  - ✓ 2-3段书面解读

- [x] **requirements.txt** - 完整依赖列表

- [x] **README.md** - 完整文档

### ⚠️ 待完成 (核心实现)

#### Module 1: Trade Parser (`src/module1_parser.py`)
需要实现:
```python
def classify_instrument(trade: dict) -> str:
    """分类: CONVENTIONAL_DERIVATIVE | NOVEL_INSTRUMENT_NO_TAXONOMY | CLASSIFICATION_AMBIGUOUS"""
    
def parse_trade(trade: dict) -> ParsedTrade:
    """
    1. 提取 asset_class, instrument_type, use_case
    2. 调用 classify_instrument()
    3. 验证 execution_timestamp (ISO 8601)
    4. 验证 effective_date, maturity_date (YYYY-MM-DD)
    5. 返回 ParsedTrade(status, errors)
    """

def parse_trades(raw_trades: List[dict]) -> List[ParsedTrade]:
    """批处理所有trades"""
```

#### Module 3: Compliance Checker (`src/module3_compliance.py`)
需要实现:
```python
def validate_lei(lei: Optional[str]) -> tuple[bool, str]:
    """ISO 7064 MOD 97-10检验"""

def validate_uti(uti: Optional[str], reporting_lei: str) -> tuple[bool, str]:
    """ISO 23897格式检验"""

def check_cftc_compliance(parsed_trade, upi_result, raw_trade) -> ComplianceResult:
    """CFTC字段验证"""

def check_emir_compliance(parsed_trade, upi_result, raw_trade) -> ComplianceResult:
    """EMIR字段验证 (包含margin字段)"""

def check_compliance_batch(parsed_trades, upi_results, raw_trades, regimes) -> List[ComplianceResult]:
    """批处理合规检查"""
```

#### Data Structures (`src/schemas.py`)
需要定义:
```python
@dataclass
class ParsedTrade:
    trade_id: str
    parse_status: str  # SUCCESS | PARTIAL | FAILED
    asset_class: str
    instrument_type: str
    use_case: str
    classification_flag: str  # CONVENTIONAL_DERIVATIVE | NOVEL_INSTRUMENT_NO_TAXONOMY | CLASSIFICATION_AMBIGUOUS
    parse_errors: List[str]
    classified_fields: Dict[str, Any]

@dataclass
class ComplianceResult:
    trade_id: str
    cftc_status: str  # COMPLIANT | NONCOMPLIANT | CONDITIONAL | NOT_APPLICABLE
    emir_status: str
    cftc_field_validations: Dict[str, Dict]  # {field_name: {value, valid, error}}
    emir_field_validations: Dict[str, Dict]
    notes: str
```

---

## 🔑 Module 2 启发式匹配完全解析

### 为什么需要启发式匹配?

**问题**:
- ANNA-DSB库有 143 个模板
- 文件名格式严格: `AssetClass.InstrumentType.UseCase.UPI.V*.json`
- Trade的 `use_case` 字段可能与库中的命名不完全相同

**例子**:
```
Trade T006: use_case = "Basis" (Basis Swap, 两腿基准)
库中: 
  - Rates.Swap.Fixed_Float.UPI.V1.json
  - Rates.Swap.OIS.UPI.V1.json
  - Rates.Swap.Basis.UPI.V1.json ← 精确匹配!

Trade T011: use_case = "CrossCurrency" (跨币种)
库中:
  - 无 "CrossCurrency" use_case
  - 启发式搜索最接近的 → 可能是 "OIS", "Basis", 或其他
```

### 两层算法

```python
# 第1层: 精确
if f"{asset_class}.{instrument_type}.{use_case}.UPI.V*.json" in directory:
    return template, 1.0

# 第2层: 启发式
best_score = 0
for template_file in all_templates:
    template_use_case = extract_use_case_from_filename(template_file)
    score = SequenceMatcher(use_case, template_use_case).ratio()
    if score > best_score:
        best_score = score
        best_match = template_file

if best_score >= 0.50:
    return template, best_score
else:
    return None, 0.0
```

### 输出中的痕迹

```json
{
  "status": "FOUND",
  "matched_template": "Rates.Swap.Basis.UPI.V1",  // 实际匹配的模板
  "classification_note": "Heuristic match (score: 0.65). Trade use_case 'CrossCurrency' did not match any exact template filename. Matched to template: Rates.Swap.Basis.UPI.V1",
  "upi_code": "E5PNQBPNQ7JLLM7THFMD"
}
```

**阅卷老师可以看到**:
1. ✓ 找到了模板 (status=FOUND)
2. ✓ 用的是哪个模板 (matched_template)
3. ✓ 这是启发式匹配 (classification_note说明)
4. ✓ 为什么要启发式 (note中解释trade的use_case不精确匹配)

---

## 📊 Module 5 Dashboard 满分要素

### 加分标准 (15分bonus)

| 标准 | 分数 | 满足方式 |
|------|------|--------|
| 4个必需可视化正确标注 | 8 | ✅ 实现了 |
| 代码可重复性:从输出文件正确生成图表 | 4 | ✅ 从JSON重建 |
| 2-3段书面解读嵌入仪表盘 | 3 | ✅ 包含解读 |

### 四个可视化详解

#### 1. **合规热力图** (Heatmap)
```
        CFTC    EMIR
T001    🟢      🟢     COMPLIANT
T002    🔴      🟢     CFTC失败
...
T026    🟠      ⚫     CONDITIONAL / NOT_APPLICABLE
T027    ⚫      ⚫     都不适用
T028    🟠      ⚫     CONDITIONAL / NOT_APPLICABLE
```

**重点**: T026-T028的非对称性一目了然!

#### 2. **字段失败频率** (Horizontal Bar)
```
reporting_counterparty_lei ████████ (10次失败)
execution_timestamp        ██████ (8次)
effective_date             ████ (4次)
...
```

**重点**: 显示哪些字段最常失败

#### 3. **资产类别分解** (Stacked Bars)
```
CFTC             EMIR
Rates:     C=2   C=6
Credit:    C=1   C=2
FX:        C=0   C=3
Equity:    C=0   C=2
Commodities: C=0 C=4
EventContract: C=0 C=0 (特殊)
```

**重点**: 按资产类别的合规率对比

#### 4. **分类边界面板** (Table)
```
| Trade | Platform | Platform Type | CFTC | EMIR |
|-------|----------|---------------|------|------|
| T026  | Kalshi   | CFTC DCM      | 🟠   | ⚫   |
| T027  | Polymarket| Offshore     | ⚫   | ⚫   |
| T028  | Kalshi   | CFTC DCM      | 🟠   | ⚫   |
```

**重点**: 清晰展示司法管辖权非对称性

### 书面解读示例结构

```markdown
## 书面解读

### 第1段: 数据质量与合规的矛盾
- 28笔交易中仅1笔CFTC合规
- 关键原因: LEI检验位失败
- 仅3个counterparty的LEI通过ISO 7064 MOD 97-10
- 启示: 合规发动于身份数据，不仅仅是报告规则

### 第2段: 司法管辖权非对称性 (中心论证)
- T026/T028: CFTC CONDITIONAL vs EMIR NOT_APPLICABLE
- 原因: CFTC尚在起草规则(ANPR 91 FR 12516)，而EU将其分类为赌博
- 影响: 13B美元/月的交易流量隐形
- 结论: 合规引擎无法报告分类尚未定的资产

### 第3段: 建议 (实用价值)
- LEI验证应在交易前，不是报告后
- 时间戳标准化到ISO 8601
- 监控CFTC预测市场规则出台
```

---

## 🚀 立即开始

### 第1步: 环境准备 (5分钟)
```bash
cd d:/6822-team
pip install -r requirements.txt
git clone https://github.com/ANNA-DSB/Product-Definitions.git data/product_definitions
```

### 第2步: 实现Module 1 (1-2小时)
**文件**: `src/module1_parser.py`

**关键要点**:
- 时间戳正则 + datetime.fromisoformat()
- 日期验证 (YYYY-MM-DD)
- Classification enum逻辑
- 错误收集不崩溃

### 第3步: 实现Module 3 (1-2小时)
**文件**: `src/module3_compliance.py`

**关键要点**:
- LEI验证: 使用`python-stdnum`或自实现MOD97-10
- UTI验证: 格式 + namespace一致性
- 司法管辖权逻辑 (T026-T028特殊处理)
- 字段逐个审计

### 第4步: 测试端到端 (30分钟)
```bash
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR
# 应该看到:
# ✅ Module 1 Complete: SUCCESS=25, PARTIAL=2, FAILED=1, Novel=3
# ✅ Module 2 Complete: FOUND=25, NO_PRODUCT_DEFINITION=3
# ✅ Module 3 Complete: 
#    CFTC: COMPLIANT=1, NONCOMPLIANT=24, CONDITIONAL=2, NOT_APPLICABLE=1
#    EMIR: COMPLIANT=25, NONCOMPLIANT=0, CONDITIONAL=0, NOT_APPLICABLE=3
# 🚀 Dashboard at http://localhost:8501
```

---

## 🎯 最高分策略

### Module 1 (20分)
- ✅ 所有28笔无崩溃
- ✅ T026-T028正确标记为NOVEL
- ✅ 时间戳/日期检验到位
- **+加分**: 添加pytest测试用例

### Module 2 (25分)
- ✅ 11个精确 + 14个启发式 = 25个FOUND
- ✅ T026-T028 = 3个NO_PRODUCT_DEFINITION
- ✅ Codeset错误信息具体
- ✅ LIBOR弃用警告
- **+加分**: 自定义相似度阈值说明

### Module 3 (25分)
- ✅ CFTC字段1个COMPLIANT
- ✅ EMIR字段25个COMPLIANT
- ✅ T026-T028司法管辖权正确
- ✅ LEI/UTI验证准确
- **+加分**: 详细的字段审计

### Module 5 (15分bonus)
- ✅ 4个图表 + 颜色编码 (8分)
- ✅ 从compliance_report.json重建 (4分)
- ✅ 2-3段解读 (3分)
- **+加分**: 交互式悬停 + 可下载报表

---

## 📞 常见问题

**Q: Heuristic matching的阈值是多少?**
A: 推荐 >= 0.50。可调范围 0.40-0.60取决于库覆盖度。在output中说明即可。

**Q: T026-T028必须得NOT_APPLICABLE吗?**
A: 不必。可以是CONDITIONAL (表示在等待分类)。关键是EMIR给NOT_APPLICABLE (EU赌博法)。

**Q: LEI必须真实有效吗?**
A: 不必。题目说 "not all real; that is part of the exercise"。验证校验位格式即可。

**Q: Dashboard可以用Jupyter替代吗?**
A: 可以。题目说 "Jupyter notebook with interactive plots or minimal web application"。Streamlit更好用。

---

## ✅ 提交前检查清单

- [ ] `python run_compliance_check.py --input trades.json --regimes CFTC,EMIR` 无错
- [ ] `output/` 有三个JSON文件
- [ ] Dashboard 显示 4 个图表
- [ ] Dashboard 包含 2-3 段书面解读
- [ ] README 清晰说明如何运行
- [ ] 代码有适当注释
- [ ] Git repo ready (所有源文件+requirements.txt+README)

---

**项目已就绪! 核心架构完整，Module 1/3 需要填充实现逻辑，Module 2 已完整。**
