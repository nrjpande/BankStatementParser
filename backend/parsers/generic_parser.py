import pandas as pd
from parsers.base_parser import BaseParser


class GenericParser(BaseParser):
    bank_name = "Generic"

    DATE_KEYWORDS = ["date", "value date", "transaction date", "txn date", "tran date", "posting date"]
    DESC_KEYWORDS = ["description", "narration", "particulars", "remarks", "details", "transaction details"]
    DEBIT_KEYWORDS = ["withdrawal", "debit", "debit amount", "dr", "debit amt", "withdrawals"]
    CREDIT_KEYWORDS = ["deposit", "credit", "credit amount", "cr", "credit amt", "deposits"]
    BALANCE_KEYWORDS = ["balance", "closing balance", "running balance", "available balance"]

    def _find_column(self, columns: list, keywords: list) -> str:
        for kw in keywords:
            for col in columns:
                if str(col).lower().strip() == kw:
                    return col
        for kw in keywords:
            for col in columns:
                if kw in str(col).lower().strip():
                    return col
        return ""

    def parse(self, df: pd.DataFrame) -> list:
        # Try to detect header row
        header_row = 0
        for idx in range(min(15, len(df))):
            row_vals = [str(v).lower() for v in df.iloc[idx].values if pd.notna(v)]
            row_text = " ".join(row_vals)
            date_match = any(kw in row_text for kw in self.DATE_KEYWORDS)
            amount_match = any(kw in row_text for kw in self.DEBIT_KEYWORDS + self.CREDIT_KEYWORDS)
            if date_match and amount_match:
                header_row = idx
                break

        if header_row > 0:
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)

        columns = list(df.columns)

        date_col = self._find_column(columns, self.DATE_KEYWORDS)
        desc_col = self._find_column(columns, self.DESC_KEYWORDS)
        debit_col = self._find_column(columns, self.DEBIT_KEYWORDS)
        credit_col = self._find_column(columns, self.CREDIT_KEYWORDS)
        balance_col = self._find_column(columns, self.BALANCE_KEYWORDS)

        # If we can't find debit/credit separately, look for a single "amount" column
        if not debit_col and not credit_col:
            for col in columns:
                if "amount" in str(col).lower():
                    debit_col = col
                    break

        renamed = pd.DataFrame()
        renamed["date"] = df[date_col] if date_col else ""
        renamed["description"] = df[desc_col] if desc_col else ""
        renamed["withdrawal"] = df[debit_col] if debit_col else 0
        renamed["deposit"] = df[credit_col] if credit_col else 0
        renamed["balance"] = df[balance_col] if balance_col else 0

        return self.to_standard_format(renamed)
