import pandas as pd
import re


def _clean(text):
    return re.sub(r'\s+', ' ', str(text).replace('\n', ' ')).lower().strip()


def detect_bank(df: pd.DataFrame) -> str:
    columns = [_clean(c) for c in df.columns]
    col_text = " ".join(columns)

    # Only check first 10 rows for bank NAME (account info area, not transaction data)
    header_text = ""
    for idx in range(min(10, len(df))):
        row_vals = [_clean(v) for v in df.iloc[idx].values if pd.notna(v)]
        header_text += " ".join(row_vals) + " "

    # For column keyword matching, check up to 40 rows
    deep_col_text = ""
    for idx in range(min(40, len(df))):
        row_vals = [_clean(v) for v in df.iloc[idx].values if pd.notna(v)]
        deep_col_text += " ".join(row_vals) + " "

    all_keywords = col_text + " " + deep_col_text

    # ---- STEP 1: Explicit bank name in header area ----
    if "hdfc" in header_text and "hdfc" in col_text:
        return "HDFC"
    if "icici" in header_text:
        return "ICICI"
    if ("state bank" in header_text or ("sbi" in header_text and "sbin" not in header_text)):
        return "SBI"
    if "axis" in header_text:
        return "AXIS"
    if "kotak" in header_text:
        return "KOTAK"
    if "idfc" in header_text:
        return "GENERIC"
    if "au small" in header_text or "au finance" in header_text:
        return "GENERIC"
    if "dbs" in header_text or "digibank" in header_text:
        return "GENERIC"
    if "bank of india" in header_text:
        return "GENERIC"

    # ---- STEP 2: Column-based detection (most reliable) ----
    # HDFC signature: "narration" column + chq/ref columns
    if "narration" in all_keywords and ("chq" in all_keywords or "ref" in all_keywords or "value dt" in all_keywords):
        return "HDFC"
    if "hdfc" in all_keywords and "narration" in all_keywords:
        return "HDFC"

    # ICICI signature: "transaction date" + "description"
    if "transaction date" in col_text and "description" in col_text:
        return "ICICI"

    # If columns have "Transaction Date" + "Particulars" + "Debit"/"Credit" -> generic (IDFC, AU, etc.)
    if "transaction date" in col_text and "particulars" in col_text:
        return "GENERIC"

    # SBI signature: "value date" column (without "transaction date")
    if "value date" in col_text and "transaction date" not in col_text:
        if "narration" not in col_text:  # Not HDFC
            return "SBI"

    # Axis: "tran date" + "particulars"
    if "tran date" in col_text and "particulars" in col_text:
        return "AXIS"

    # ---- STEP 3: Fallback column keyword checks ----
    if "narration" in col_text:
        return "HDFC"
    if "transaction date" in col_text:
        return "ICICI"
    if "value date" in col_text:
        return "SBI"
    if "particulars" in col_text:
        return "GENERIC"

    # ---- STEP 4: Deep scan in data rows ----
    if "narration" in deep_col_text and "chq" in deep_col_text:
        return "HDFC"
    if "narration" in deep_col_text:
        return "HDFC"
    if "transaction date" in deep_col_text and "particulars" in deep_col_text:
        return "GENERIC"
    if "transaction date" in deep_col_text:
        return "ICICI"
    if "particulars" in deep_col_text:
        return "GENERIC"

    return "GENERIC"


def get_parser(bank: str):
    from parsers.hdfc_parser import HDFCParser
    from parsers.icici_parser import ICICIParser
    from parsers.sbi_parser import SBIParser
    from parsers.axis_parser import AxisParser
    from parsers.kotak_parser import KotakParser
    from parsers.generic_parser import GenericParser

    parsers = {
        "HDFC": HDFCParser,
        "ICICI": ICICIParser,
        "SBI": SBIParser,
        "AXIS": AxisParser,
        "KOTAK": KotakParser,
        "GENERIC": GenericParser,
    }
    return parsers.get(bank, GenericParser)()
