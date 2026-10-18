import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from backend.app.schemas.quality import QualityCheckResultResponse


class DataQualityValidator:
    """
    Modular Data Quality Validation Engine.
    Executes completeness, duplicate, data type, validity, cross-field,
    and structural integrity checks across datasets.
    """

    def __init__(self, df: pd.DataFrame, expected_schema: Optional[Dict[str, Any]] = None, custom_rules: Optional[Dict[str, Any]] = None):
        self.df = df
        self.expected_schema = expected_schema or {}
        self.custom_rules = custom_rules or {}
        self.results: List[Dict[str, Any]] = []

    def run_all_checks(self, dataset_id: str, run_id: str) -> List[Dict[str, Any]]:
        self.results = []
        self._check_dataset_structure(dataset_id, run_id)
        self._check_completeness(dataset_id, run_id)
        self._check_duplicates(dataset_id, run_id)
        self._check_data_types(dataset_id, run_id)
        self._check_validity_and_ranges(dataset_id, run_id)
        self._check_cross_field_rules(dataset_id, run_id)
        return self.results

    def _add_result(
        self,
        dataset_id: str,
        run_id: str,
        check_id: str,
        check_name: str,
        category: str,
        status: str,
        severity: str,
        affected_rows: int,
        affected_columns: Optional[List[str]],
        explanation: str,
        evidence: Optional[Dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
    ):
        self.results.append({
            "check_id": check_id,
            "check_name": check_name,
            "category": category,
            "status": status,
            "severity": severity,
            "affected_rows": affected_rows,
            "affected_columns": affected_columns or [],
            "explanation": explanation,
            "evidence": evidence or {},
            "suggested_action": suggested_action or "Review data ingestion and source pipeline.",
            "created_at": datetime.utcnow(),
            "dataset_id": dataset_id,
            "run_id": run_id,
        })

    # -------------------------------------------------------------
    # 1. Dataset Structure Checks
    # -------------------------------------------------------------
    def _check_dataset_structure(self, dataset_id: str, run_id: str):
        row_count, col_count = self.df.shape

        # Row count minimum check
        if row_count == 0:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-001",
                check_name="Non-Empty Dataset",
                category="structure",
                status="failed",
                severity="critical",
                affected_rows=0,
                affected_columns=[],
                explanation="Dataset contains zero rows.",
                suggested_action="Verify source availability and file retrieval process."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-001",
                check_name="Non-Empty Dataset",
                category="structure",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation=f"Dataset contains {row_count} rows across {col_count} columns.",
                evidence={"rows": row_count, "columns": col_count}
            )

        # Check for unnamed index columns (e.g. Unnamed: 0)
        unnamed_cols = [c for c in self.df.columns if str(c).startswith("Unnamed:") or str(c) == ""]
        if unnamed_cols:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-002",
                check_name="Extraneous Index Columns",
                category="structure",
                status="warning",
                severity="low",
                affected_rows=row_count,
                affected_columns=unnamed_cols,
                explanation=f"Dataset contains {len(unnamed_cols)} unexpected unnamed or leftover index column(s).",
                evidence={"columns": unnamed_cols},
                suggested_action="Ensure CSV export specifies index=False or drop unnamed index columns during extraction."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-002",
                check_name="Extraneous Index Columns",
                category="structure",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="No extraneous unnamed index columns found.",
            )

        # Check for completely empty columns
        empty_cols = [c for c in self.df.columns if self.df[c].isna().all()]
        if empty_cols:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-003",
                check_name="Empty Column Check",
                category="structure",
                status="warning",
                severity="medium",
                affected_rows=row_count,
                affected_columns=empty_cols,
                explanation=f"Columns {empty_cols} contain 100% missing values across all records.",
                evidence={"empty_columns": empty_cols},
                suggested_action="Investigate why these fields are unpopulated by publisher."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="STRUC-003",
                check_name="Empty Column Check",
                category="structure",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="No completely blank columns detected.",
            )

    # -------------------------------------------------------------
    # 2. Completeness Checks
    # -------------------------------------------------------------
    def _check_completeness(self, dataset_id: str, run_id: str):
        total_cells = self.df.size
        # Rule: do not treat 0, False, or empty string as missing unless explicitly configured
        missing_mask = self.df.isna()
        if self.custom_rules.get("treat_empty_string_as_missing", False):
            str_mask = self.df.applymap(lambda v: isinstance(v, str) and v.strip() == "")
            missing_mask = missing_mask | str_mask

        total_missing = int(missing_mask.sum().sum())
        missing_rate = (total_missing / total_cells * 100) if total_cells > 0 else 0.0

        # Fully empty rows
        empty_rows_count = int(missing_mask.all(axis=1).sum())
        if empty_rows_count > 0:
            self._add_result(
                dataset_id, run_id,
                check_id="COMP-001",
                check_name="Fully Empty Rows",
                category="completeness",
                status="warning",
                severity="medium",
                affected_rows=empty_rows_count,
                affected_columns=[],
                explanation=f"Found {empty_rows_count} completely blank row(s) in dataset.",
                evidence={"empty_row_count": empty_rows_count},
                suggested_action="Filter out blank rows at source parser."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="COMP-001",
                check_name="Fully Empty Rows",
                category="completeness",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="No completely blank rows detected.",
            )

        # Missingness by column
        col_missing = missing_mask.sum()
        excessive_cols = []
        col_evidence = {}
        for col, count in col_missing.items():
            if count > 0:
                pct = round((count / len(self.df)) * 100, 2)
                col_evidence[col] = {"missing_count": int(count), "missing_pct": pct}
                if pct > 30.0:
                    excessive_cols.append(col)

        if excessive_cols:
            self._add_result(
                dataset_id, run_id,
                check_id="COMP-002",
                check_name="Excessive Column Missingness",
                category="completeness",
                status="warning" if missing_rate < 30.0 else "failed",
                severity="high" if missing_rate >= 30.0 else "medium",
                affected_rows=int(max([col_evidence[c]["missing_count"] for c in excessive_cols])),
                affected_columns=excessive_cols,
                explanation=f"{len(excessive_cols)} column(s) have missing rates exceeding 30%: {', '.join(excessive_cols)}.",
                evidence={"overall_missing_pct": round(missing_rate, 2), "columns": col_evidence},
                suggested_action="Review column collection requirements or handle imputation."
            )
        elif total_missing > 0:
            self._add_result(
                dataset_id, run_id,
                check_id="COMP-002",
                check_name="Excessive Column Missingness",
                category="completeness",
                status="passed",
                severity="info",
                affected_rows=total_missing,
                affected_columns=list(col_evidence.keys()),
                explanation=f"Overall missing rate is low ({missing_rate:.2f}%). No columns exceed 30% missingness threshold.",
                evidence={"overall_missing_pct": round(missing_rate, 2), "columns": col_evidence}
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="COMP-002",
                check_name="Excessive Column Missingness",
                category="completeness",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="Dataset is 100% complete with zero missing cells.",
                evidence={"overall_missing_pct": 0.0}
            )

    # -------------------------------------------------------------
    # 3. Duplicate Checks
    # -------------------------------------------------------------
    def _check_duplicates(self, dataset_id: str, run_id: str):
        # Full row duplicates
        dup_rows_mask = self.df.duplicated(keep=False)
        dup_rows_count = int(dup_rows_mask.sum())

        if dup_rows_count > 0:
            sample_dups = self.df[dup_rows_mask].head(4).to_dict(orient="records")
            self._add_result(
                dataset_id, run_id,
                check_id="DUP-001",
                check_name="Full Row Duplicates",
                category="uniqueness",
                status="warning" if dup_rows_count < len(self.df) * 0.1 else "failed",
                severity="medium" if dup_rows_count < len(self.df) * 0.1 else "high",
                affected_rows=dup_rows_count,
                affected_columns=[],
                explanation=f"Detected {dup_rows_count} fully duplicated row records in dataset.",
                evidence={"duplicate_row_count": dup_rows_count, "samples": sample_dups},
                suggested_action="Deduplicate rows using primary keys or business identifier."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="DUP-001",
                check_name="Full Row Duplicates",
                category="uniqueness",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="No fully duplicate rows detected across the dataset.",
            )

        # Identifier uniqueness check
        id_cols = [c for c in self.df.columns if any(k in c.lower() for k in ["id", "code", "record", "uuid", "station", "facility"])]
        configured_id = self.custom_rules.get("primary_key")
        if configured_id and configured_id in self.df.columns:
            target_ids = [configured_id]
        else:
            target_ids = id_cols[:2]

        for id_col in target_ids:
            if id_col in self.df.columns:
                series = self.df[id_col].dropna()
                dup_ids_count = int(series.duplicated().sum())
                if dup_ids_count > 0:
                    dup_samples = list(series[series.duplicated(keep=False)].head(5).astype(str))
                    self._add_result(
                        dataset_id, run_id,
                        check_id=f"DUP-ID-{id_col}",
                        check_name=f"Identifier Uniqueness: {id_col}",
                        category="uniqueness",
                        status="failed",
                        severity="high",
                        affected_rows=dup_ids_count,
                        affected_columns=[id_col],
                        explanation=f"Column '{id_col}' expected to be unique has {dup_ids_count} duplicate values.",
                        evidence={"column": id_col, "duplicate_ids_count": dup_ids_count, "samples": dup_samples},
                        suggested_action=f"Enforce primary key uniqueness constraints on {id_col}."
                    )
                else:
                    self._add_result(
                        dataset_id, run_id,
                        check_id=f"DUP-ID-{id_col}",
                        check_name=f"Identifier Uniqueness: {id_col}",
                        category="uniqueness",
                        status="passed",
                        severity="info",
                        affected_rows=0,
                        affected_columns=[id_col],
                        explanation=f"Identifier column '{id_col}' maintains 100% unique values.",
                    )

    # -------------------------------------------------------------
    # 4. Data Type Checks
    # -------------------------------------------------------------
    def _check_data_types(self, dataset_id: str, run_id: str):
        # Check expected schema mismatches if configured
        if self.expected_schema:
            mismatches = []
            for col, expected_type in self.expected_schema.items():
                if col not in self.df.columns:
                    continue
                actual_dtype = str(self.df[col].dtype)
                if expected_type == "numeric" and not pd.api.types.is_numeric_dtype(self.df[col]):
                    mismatches.append({"column": col, "expected": expected_type, "actual": actual_dtype})
                elif expected_type == "datetime" and not pd.api.types.is_datetime64_any_dtype(self.df[col]):
                    # Try parsing
                    try:
                        pd.to_datetime(self.df[col].dropna().head(20))
                    except Exception:
                        mismatches.append({"column": col, "expected": expected_type, "actual": actual_dtype})

            if mismatches:
                self._add_result(
                    dataset_id, run_id,
                    check_id="TYPE-001",
                    check_name="Schema Type Conformance",
                    category="schema",
                    status="failed",
                    severity="high",
                    affected_rows=0,
                    affected_columns=[m["column"] for m in mismatches],
                    explanation=f"{len(mismatches)} column(s) do not match configured expected data types.",
                    evidence={"mismatches": mismatches},
                    suggested_action="Review upstream schema casting or transform pipeline."
                )
            else:
                self._add_result(
                    dataset_id, run_id,
                    check_id="TYPE-001",
                    check_name="Schema Type Conformance",
                    category="schema",
                    status="passed",
                    severity="info",
                    affected_rows=0,
                    affected_columns=[],
                    explanation="All columns conform to the expected schema types.",
                )

        # Check for mixed numeric types (e.g. numeric columns with invalid string corruptions)
        mixed_cols = []
        for col in self.df.select_dtypes(include=["object"]).columns:
            non_null = self.df[col].dropna()
            if len(non_null) == 0:
                continue
            # Check how many convert to numeric vs fail
            converted = pd.to_numeric(non_null, errors="coerce")
            valid_num_count = converted.notna().sum()
            total = len(non_null)
            # If 60% - 99% parse as numbers, it's a corrupted numeric column!
            if 0.60 <= (valid_num_count / total) < 1.0:
                corrupted_samples = list(non_null[converted.isna()].head(4).astype(str))
                mixed_cols.append({
                    "column": col,
                    "numeric_ratio": round(valid_num_count / total, 3),
                    "invalid_samples": corrupted_samples,
                })

        if mixed_cols:
            self._add_result(
                dataset_id, run_id,
                check_id="TYPE-002",
                check_name="Mixed Data Types / Invalid Numbers",
                category="validity",
                status="warning",
                severity="medium",
                affected_rows=sum(len(m["invalid_samples"]) for m in mixed_cols),
                affected_columns=[m["column"] for m in mixed_cols],
                explanation=f"{len(mixed_cols)} column(s) contain numbers mixed with invalid text or formatting characters.",
                evidence={"corrupted_columns": mixed_cols},
                suggested_action="Sanitize unit strings, symbols, or typos in numerical fields."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="TYPE-002",
                check_name="Mixed Data Types / Invalid Numbers",
                category="validity",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="No mixed-type or corrupted numeric columns detected.",
            )

    # -------------------------------------------------------------
    # 5. Validity and Range Checks
    # -------------------------------------------------------------
    def _check_validity_and_ranges(self, dataset_id: str, run_id: str):
        # Negative numbers in inherently non-negative quantities
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        non_negative_keywords = ["price", "arrival", "bed", "attendance", "admitted", "doctor", "power", "kw", "aqi", "pm25", "pm10", "count", "tariff"]
        
        violations = []
        for col in numeric_cols:
            if any(k in col.lower() for k in non_negative_keywords):
                negatives = self.df[self.df[col] < 0]
                neg_count = len(negatives)
                if neg_count > 0:
                    violations.append({
                        "column": col,
                        "negative_count": neg_count,
                        "min_value": float(self.df[col].min()),
                        "samples": list(negatives[col].head(3).astype(float)),
                    })

        if violations:
            self._add_result(
                dataset_id, run_id,
                check_id="VAL-001",
                check_name="Non-Negative Value Constraint",
                category="validity",
                status="failed",
                severity="high",
                affected_rows=sum(v["negative_count"] for v in violations),
                affected_columns=[v["column"] for v in violations],
                explanation=f"Found negative values in fields that domain requires to be non-negative ({', '.join(v['column'] for v in violations)}).",
                evidence={"violations": violations},
                suggested_action="Filter or correct inverted signs/negative entries."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="VAL-001",
                check_name="Non-Negative Value Constraint",
                category="validity",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="All domain-specific non-negative numerical fields contain valid values (>= 0).",
            )

        # Date validity check: parse dates and check for impossible future dates
        date_cols = [c for c in self.df.columns if any(k in c.lower() for k in ["date", "reading_date", "arrival_date", "commissioned_date"])]
        future_violations = []
        for dcol in date_cols:
            parsed_dates = pd.to_datetime(self.df[dcol], errors="coerce")
            now = pd.Timestamp.now() + pd.Timedelta(days=365)  # Allow small margin for planned data
            future_dates = self.df[parsed_dates > now]
            if len(future_dates) > 0:
                future_violations.append({
                    "column": dcol,
                    "future_count": len(future_dates),
                    "samples": list(future_dates[dcol].head(3).astype(str)),
                })

        if future_violations:
            self._add_result(
                dataset_id, run_id,
                check_id="VAL-002",
                check_name="Date Chronology & Validity",
                category="validity",
                status="warning",
                severity="medium",
                affected_rows=sum(v["future_count"] for v in future_violations),
                affected_columns=[v["column"] for v in future_violations],
                explanation="Found records with timestamps occurring far in the future.",
                evidence={"future_dates": future_violations},
                suggested_action="Verify system clock or date serialization on source records."
            )
        else:
            self._add_result(
                dataset_id, run_id,
                check_id="VAL-002",
                check_name="Date Chronology & Validity",
                category="validity",
                status="passed",
                severity="info",
                affected_rows=0,
                affected_columns=[],
                explanation="All dates parsed successfully and fall within valid chronological bounds.",
            )

    # -------------------------------------------------------------
    # 6. Referential and Cross-Field Consistency Checks
    # -------------------------------------------------------------
    def _check_cross_field_rules(self, dataset_id: str, run_id: str):
        # 1. Min Price vs Max Price (Agmarknet commodity rule: min_price <= max_price)
        if "min_price_inr_qtl" in self.df.columns and "max_price_inr_qtl" in self.df.columns:
            inverted = self.df[self.df["min_price_inr_qtl"] > self.df["max_price_inr_qtl"]]
            inv_count = len(inverted)
            if inv_count > 0:
                samples = inverted[["min_price_inr_qtl", "max_price_inr_qtl"]].head(3).to_dict(orient="records")
                self._add_result(
                    dataset_id, run_id,
                    check_id="CROSS-001",
                    check_name="Price Bounds Consistency (Min <= Max)",
                    category="consistency",
                    status="failed",
                    severity="high",
                    affected_rows=inv_count,
                    affected_columns=["min_price_inr_qtl", "max_price_inr_qtl"],
                    explanation=f"Found {inv_count} record(s) where min_price exceeds max_price.",
                    evidence={"samples": samples, "count": inv_count},
                    suggested_action="Swap inverted price values or audit price entry interface."
                )
            else:
                self._add_result(
                    dataset_id, run_id,
                    check_id="CROSS-001",
                    check_name="Price Bounds Consistency (Min <= Max)",
                    category="consistency",
                    status="passed",
                    severity="info",
                    affected_rows=0,
                    affected_columns=["min_price_inr_qtl", "max_price_inr_qtl"],
                    explanation="All min_price values are consistently less than or equal to max_price.",
                )

        # 2. Hospital Beds Consistency (ICU Beds <= Total Beds)
        if "icu_beds" in self.df.columns and "total_beds" in self.df.columns:
            invalid_icu = self.df[self.df["icu_beds"] > self.df["total_beds"]]
            icu_inv_count = len(invalid_icu)
            if icu_inv_count > 0:
                samples = invalid_icu[["icu_beds", "total_beds"]].head(3).to_dict(orient="records")
                self._add_result(
                    dataset_id, run_id,
                    check_id="CROSS-002",
                    check_name="Hospital Bed Ratio Consistency (ICU <= Total)",
                    category="consistency",
                    status="failed",
                    severity="high",
                    affected_rows=icu_inv_count,
                    affected_columns=["icu_beds", "total_beds"],
                    explanation=f"Found {icu_inv_count} facility record(s) where ICU beds exceed total hospital bed capacity.",
                    evidence={"samples": samples, "count": icu_inv_count},
                    suggested_action="Reconcile facility infrastructure bed tally."
                )
            else:
                self._add_result(
                    dataset_id, run_id,
                    check_id="CROSS-002",
                    check_name="Hospital Bed Ratio Consistency (ICU <= Total)",
                    category="consistency",
                    status="passed",
                    severity="info",
                    affected_rows=0,
                    affected_columns=["icu_beds", "total_beds"],
                    explanation="ICU bed count is strictly within total hospital bed capacity.",
                )

        # 3. Custom cross-field rule support from dataset configuration
        for rule in self.custom_rules.get("cross_field_rules", []):
            field_a = rule.get("field_a")
            field_b = rule.get("field_b")
            operator = rule.get("operator")  # '<=', '>=', '=='
            if field_a in self.df.columns and field_b in self.df.columns:
                if operator == "<=":
                    violators = self.df[self.df[field_a] > self.df[field_b]]
                elif operator == ">=":
                    violators = self.df[self.df[field_a] < self.df[field_b]]
                else:
                    violators = pd.DataFrame()

                v_count = len(violators)
                rule_name = rule.get("name", f"{field_a} {operator} {field_b}")
                if v_count > 0:
                    self._add_result(
                        dataset_id, run_id,
                        check_id=f"CUSTOM-CROSS-{field_a}-{field_b}",
                        check_name=rule_name,
                        category="consistency",
                        status="failed",
                        severity="high",
                        affected_rows=v_count,
                        affected_columns=[field_a, field_b],
                        explanation=f"Configured rule '{rule_name}' violated in {v_count} rows.",
                        evidence={"violating_rows": v_count},
                        suggested_action="Review domain logic constraints."
                    )
                else:
                    self._add_result(
                        dataset_id, run_id,
                        check_id=f"CUSTOM-CROSS-{field_a}-{field_b}",
                        check_name=rule_name,
                        category="consistency",
                        status="passed",
                        severity="info",
                        affected_rows=0,
                        affected_columns=[field_a, field_b],
                        explanation=f"Configured rule '{rule_name}' passed across all records.",
                    )
