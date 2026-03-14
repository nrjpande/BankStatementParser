import pandas as pd
from parsers.base_parser import BaseParser


class HDFCParser(BaseParser):
    bank_name = "HDFC"

    HEADER_KEYWORDS = ["date", "narration", "withdrawal", "deposit", "debit", "credit", "closing"]

    def parse(self, df: pd.DataFrame) -> list:
        header_row = self.detect_header_row(df, self.HEADER_KEYWORDS, max_scan=40)
        if header_row > 0:
            df.columns = [str(c).strip() for c in df.iloc[header_row].values]
            df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Skip separator rows (rows full of asterisks)
        df = df[~df.apply(lambda r: all(str(v).startswith('*') for v in r.values if pd.notna(v) and str(v).strip()), axis=1)].reset_index(drop=True)

        col_map = {}
        for col in df.columns:
            if pd.isna(col):
                continue
            cl = str(col).lower().strip()
            if cl in ("date",) or ("date" in cl and "value" not in cl):
                col_map["date"] = col
            elif "value" in cl and "dt" in cl:
                col_map.setdefault("date", col)
            elif "narration" in cl or "description" in cl or "particular" in cl:
                col_map["description"] = col
            elif "withdrawal" in cl or "debit" in cl:
                col_map["withdrawal"] = col
            elif "deposit" in cl or "credit" in cl:
                col_map["deposit"] = col
            elif "closing" in cl or "balance" in cl:
                col_map["balance"] = col

        if "date" not in col_map or "description" not in col_map:
            # Fallback: try first columns
            cols = [c for c in df.columns if pd.notna(c)]
            if len(cols) >= 5:
                col_map.setdefault("date", cols[0])
                col_map.setdefault("description", cols[1])
                col_map.setdefault("withdrawal", cols[3] if len(cols) > 3 else cols[2])
                col_map.setdefault("deposit", cols[4] if len(cols) > 4 else cols[3])
                col_map.setdefault("balance", cols[5] if len(cols) > 5 else cols[4])

        renamed = pd.DataFrame()
        renamed["date"] = df[col_map["date"]] if "date" in col_map else ""
        renamed["description"] = df[col_map["description"]] if "description" in col_map else ""
        renamed["withdrawal"] = df[col_map["withdrawal"]] if "withdrawal" in col_map else 0
        renamed["deposit"] = df[col_map["deposit"]] if "deposit" in col_map else 0
        renamed["balance"] = df[col_map["balance"]] if "balance" in col_map else 0

        return self.to_standard_format(renamed)
