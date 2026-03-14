import pandas as pd
from parsers.base_parser import BaseParser


class AxisParser(BaseParser):
    bank_name = "Axis"

    def parse(self, df: pd.DataFrame) -> list:
        header_row = self.detect_header_row(df, ["tran date", "particulars", "debit", "credit"])
        if header_row > 0:
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)

        col_map = {}
        for col in df.columns:
            cl = str(col).lower().strip()
            if "tran" in cl and "date" in cl:
                col_map["date"] = col
            elif "date" in cl and "date" not in col_map:
                col_map["date"] = col
            elif "particulars" in cl or "description" in cl or "narration" in cl:
                col_map["description"] = col
            elif "withdrawal" in cl or "debit" in cl:
                col_map["withdrawal"] = col
            elif "deposit" in cl or "credit" in cl:
                col_map["deposit"] = col
            elif "balance" in cl:
                col_map["balance"] = col

        renamed = pd.DataFrame()
        renamed["date"] = df[col_map["date"]] if "date" in col_map else ""
        renamed["description"] = df[col_map["description"]] if "description" in col_map else ""
        renamed["withdrawal"] = df[col_map["withdrawal"]] if "withdrawal" in col_map else 0
        renamed["deposit"] = df[col_map["deposit"]] if "deposit" in col_map else 0
        renamed["balance"] = df[col_map["balance"]] if "balance" in col_map else 0

        return self.to_standard_format(renamed)
