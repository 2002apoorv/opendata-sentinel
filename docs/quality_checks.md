# Data Quality Validation Check Catalog

OpenData Sentinel implements a formal data quality checking engine. Every check generates a structured result containing check identifier, status, severity, affected scope, technical evidence, and actionable remediation instructions.

| Check ID | Check Name | Category | Statuses | Default Severity | Description & Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STRUC-001** | Non-Empty Dataset | Structure | passed, failed | Critical | Verifies that dataset contains $\ge 1$ parsed row records. |
| **STRUC-002** | Extraneous Index Columns | Structure | passed, warning | Low | Flags leftover unnamed CSV index artifacts (e.g. `Unnamed: 0`). |
| **STRUC-003** | Empty Column Check | Structure | passed, warning | Medium | Detects columns where 100% of rows contain missing null values. |
| **COMP-001** | Fully Empty Rows | Completeness | passed, warning | Medium | Flags rows where every column cell is empty. |
| **COMP-002** | Excessive Column Missingness | Completeness | passed, warning, failed | High / Critical | Tracks column missing percentages. Triggers warning at $> 30\%$, failure at $> 70\%$. |
| **DUP-001** | Full Row Duplicates | Uniqueness | passed, warning, failed | Medium / High | Detects identical row duplicates across all columns. |
| **DUP-ID-\*** | Identifier Uniqueness | Uniqueness | passed, failed | Critical | Enforces primary key uniqueness on configured or inferred ID columns. |
| **TYPE-001** | Schema Type Conformance | Schema | passed, failed | High | Validates inferred types against expected schema definitions. |
| **TYPE-002** | Mixed Numeric Types | Validity | passed, warning | Medium | Flags numerical columns containing invalid text, unit strings, or typos. |
| **VAL-001** | Non-Negative Value Constraint | Validity | passed, failed | High | Enforces non-negative bounds ($x \ge 0$) on prices, bed counts, and quantities. |
| **VAL-002** | Date Chronology & Validity | Validity | passed, warning | Medium | Verifies that dates parse cleanly and do not point to impossible future years. |
| **CROSS-001** | Price Bounds Consistency | Consistency | passed, failed | High | Validates that agricultural commodity `min_price <= max_price`. |
| **CROSS-002** | Hospital Bed Ratio Consistency | Consistency | passed, failed | High | Enforces facility capacity rule: `icu_beds <= total_beds`. |
| **CUSTOM-CROSS-\*** | Custom Cross-Field Rules | Consistency | passed, failed | Configurable | Evaluates user-configured relational rules (e.g. `<=`, `>=`, `==`). |

---

## Result Schema Format

Each check outputs the following structured JSON response:
```json
{
  "check_id": "CROSS-001",
  "check_name": "Price Bounds Consistency (Min <= Max)",
  "category": "consistency",
  "status": "failed",
  "severity": "high",
  "affected_rows": 5,
  "affected_columns": ["min_price_inr_qtl", "max_price_inr_qtl"],
  "explanation": "Found 5 record(s) where min_price exceeds max_price.",
  "evidence": {
    "count": 5,
    "samples": [
      {"min_price_inr_qtl": 9999.0, "max_price_inr_qtl": 1200.0}
    ]
  },
  "suggested_action": "Swap inverted price values or audit price entry interface."
}
```
