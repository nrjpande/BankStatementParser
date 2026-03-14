import pandas as pd


def detect_bank(df: pd.DataFrame) -> str:
    columns = [str(c).lower().strip() for c in df.columns]
    all_text = " ".join(columns)

    # Also check first 15 rows for header keywords
    sample_text = ""
    for idx in range(min(15, len(df))):
        row_vals = [str(v).lower() for v in df.iloc[idx].values if pd.notna(v)]
        sample_text += " ".join(row_vals) + " "

    combined = all_text + " " + sample_text

    if "narration" in combined and ("chq" in combined or "ref" in combined or "value dt" in combined):
        return "HDFC"
    if "narration" in all_text and "withdrawal" not in all_text:
        return "HDFC"
    if "transaction date" in combined or ("tran date" in combined and "icici" in combined.lower()):
        return "ICICI"
    if "value date" in combined and ("sbi" in combined or "state bank" in combined):
        return "SBI"
    if "axis" in combined and ("tran date" in combined or "particulars" in combined):
        return "AXIS"
    if "kotak" in combined or ("description" in combined and "kotak" in combined):
        return "KOTAK"
    if "value date" in all_text:
        return "SBI"
    if "narration" in all_text:
        return "HDFC"
    if "transaction date" in all_text:
        return "ICICI"
    if "particulars" in all_text:
        return "AXIS"

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
