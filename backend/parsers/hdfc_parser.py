import pandas as pd
import re
from parsers.base_parser import BaseParser


class HDFCParser(BaseParser):
    bank_name = "HDFC"

    HEADER_KEYWORDS = ["date", "narration", "withdrawal", "deposit", "debit", "credit", "closing"]

    def parse(self, df: pd.DataFrame) -> list:
        # Clean column names
        df.columns = [re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip() for c in df.columns]

        # Check if current columns already look like headers
        col_text = " ".join(str(c).lower() for c in df.columns)
        has_good_headers = ("date" in col_text) and (
            "narration" in col_text or "description" in col_text
        ) and ("withdrawal" in col_text or "debit" in col_text or "deposit" in col_text or "credit" in col_text)

        if not has_good_headers:
            header_row = self.detect_header_row(df, self.HEADER_KEYWORDS, max_scan=40)
            if header_row > 0:
                df.columns = [re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip()
                              for c in df.iloc[header_row].values]
                df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Skip separator rows (asterisks)
        df = df[~df.apply(lambda r: all(
            str(v).startswith('*') for v in r.values if pd.notna(v) and str(v).strip()
        ), axis=1)].reset_index(drop=True)

        col_map = {}
        for col in df.columns:
            if pd.isna(col):
                continue
            cl = str(col).lower().strip()
            if cl in ("date",) or ("date" in cl and "value" not in cl):
                col_map["date"] = col
            elif "value" in cl and ("dt" in cl or "date" in cl):
                col_map.setdefault("date", col)
            elif "narration" in cl or "description" in cl or "particular" in cl:
                col_map["description"] = col
            elif "withdrawal" in cl or "debit" in cl:
                col_map["withdrawal"] = col
            elif "deposit" in cl or "credit" in cl:
                col_map["deposit"] = col
            elif "closing" in cl or "balance" in cl:
                col_map["balance"] = col

        renamed = pd.DataFrame()
        renamed["date"] = df[col_map["date"]] if "date" in col_map else ""
        renamed["description"] = df[col_map["description"]] if "description" in col_map else ""
        renamed["withdrawal"] = df[col_map["withdrawal"]] if "withdrawal" in col_map else 0
        renamed["deposit"] = df[col_map["deposit"]] if "deposit" in col_map else 0
        renamed["balance"] = df[col_map["balance"]] if "balance" in col_map else 0

        # Merge continuation rows (rows without a date are continuations of previous narration)
        merged_rows = []
        for _, row in renamed.iterrows():
            date_val = self.clean_date(row.get("date", ""))
            desc_val = self.clean_description(row.get("description", ""))

            if date_val and desc_val:
                merged_rows.append({
                    "date": date_val,
                    "description": desc_val,
                    "withdrawal": self.clean_amount(row.get("withdrawal", 0)),
                    "deposit": self.clean_amount(row.get("deposit", 0)),
                    "balance": self.clean_amount(row.get("balance", 0)),
                })
            elif not date_val and desc_val and merged_rows:
                # Continuation row - append description to previous
                merged_rows[-1]["description"] += " " + desc_val
                # If this row has amounts and the previous didn't, use them
                w = self.clean_amount(row.get("withdrawal", 0))
                d = self.clean_amount(row.get("deposit", 0))
                if w > 0 and merged_rows[-1]["withdrawal"] == 0:
                    merged_rows[-1]["withdrawal"] = w
                if d > 0 and merged_rows[-1]["deposit"] == 0:
                    merged_rows[-1]["deposit"] = d

        # Filter valid transactions
        return [t for t in merged_rows if t["date"] and (t["withdrawal"] > 0 or t["deposit"] > 0)]
