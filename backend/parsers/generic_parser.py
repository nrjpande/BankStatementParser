import pandas as pd
import re
from parsers.base_parser import BaseParser


class GenericParser(BaseParser):
    bank_name = "Generic"

    DATE_KEYWORDS = [
        "date", "value date", "transaction date", "txn date", "tran date",
        "posting date", "transaction date / emi due date", "trans date"
    ]
    DESC_KEYWORDS = [
        "description", "narration", "particulars", "remarks", "details",
        "transaction details", "transaction description"
    ]
    DEBIT_KEYWORDS = [
        "withdrawal", "debit", "debit amount", "dr", "dr.", "debit amt",
        "withdrawals", "withdrawal amt", "withdrawal amt.", "withdrawalamt."
    ]
    CREDIT_KEYWORDS = [
        "deposit", "credit", "credit amount", "cr", "cr.", "credit amt",
        "deposits", "deposit amt", "deposit amt.", "depositamt."
    ]
    BALANCE_KEYWORDS = [
        "balance", "closing balance", "running balance", "available balance",
        "closingbalance"
    ]

    def _clean_col(self, col):
        """Normalize column name for matching."""
        if pd.isna(col):
            return ""
        return re.sub(r'\s+', ' ', str(col).replace('\n', ' ')).lower().strip()

    def _find_column(self, columns: list, keywords: list) -> str:
        cleaned_map = {col: self._clean_col(col) for col in columns}
        # Exact match first
        for kw in keywords:
            for col, cl in cleaned_map.items():
                if cl == kw:
                    return col
        # Partial match
        for kw in keywords:
            for col, cl in cleaned_map.items():
                if kw in cl:
                    return col
        return ""

    def parse(self, df: pd.DataFrame) -> list:
        # Clean column names
        df.columns = [re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip() for c in df.columns]

        # Try to detect header row if columns don't look right
        all_keywords = self.DATE_KEYWORDS + self.DESC_KEYWORDS + self.DEBIT_KEYWORDS + self.CREDIT_KEYWORDS
        col_text = " ".join(self._clean_col(c) for c in df.columns)
        has_header = any(kw in col_text for kw in self.DATE_KEYWORDS) and any(
            kw in col_text for kw in self.DEBIT_KEYWORDS + self.CREDIT_KEYWORDS
        )

        if not has_header:
            header_row = self.detect_header_row(df, all_keywords, max_scan=40)
            if header_row > 0:
                df.columns = [re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip()
                              for c in df.iloc[header_row].values]
                df = df.iloc[header_row + 1:].reset_index(drop=True)

        columns = list(df.columns)

        date_col = self._find_column(columns, self.DATE_KEYWORDS)
        desc_col = self._find_column(columns, self.DESC_KEYWORDS)
        debit_col = self._find_column(columns, self.DEBIT_KEYWORDS)
        credit_col = self._find_column(columns, self.CREDIT_KEYWORDS)
        balance_col = self._find_column(columns, self.BALANCE_KEYWORDS)

        # If no debit/credit, look for a single "amount" column
        if not debit_col and not credit_col:
            for col in columns:
                if "amount" in self._clean_col(col):
                    debit_col = col
                    break

        # If no description found, try second column
        if not desc_col and date_col and len(columns) >= 2:
            date_idx = columns.index(date_col)
            for i, col in enumerate(columns):
                if i != date_idx and col != debit_col and col != credit_col and col != balance_col:
                    desc_col = col
                    break

        renamed = pd.DataFrame()
        renamed["date"] = df[date_col] if date_col else ""
        renamed["description"] = df[desc_col] if desc_col else ""
        renamed["withdrawal"] = df[debit_col] if debit_col else 0
        renamed["deposit"] = df[credit_col] if credit_col else 0
        renamed["balance"] = df[balance_col] if balance_col else 0

        # Merge continuation rows (rows without a date are continuations of previous narration)
        merged_rows = []
        for _, row in renamed.iterrows():
            date_val = self.clean_date(row.get("date", ""))
            desc_val = self.clean_description(row.get("description", ""))

            if date_val:
                merged_rows.append({
                    "date": date_val,
                    "description": desc_val,
                    "withdrawal": self.clean_amount(row.get("withdrawal", 0)),
                    "deposit": self.clean_amount(row.get("deposit", 0)),
                    "balance": self.clean_amount(row.get("balance", 0)),
                })
            elif desc_val and merged_rows:
                # Continuation row
                merged_rows[-1]["description"] += " " + desc_val
                w = self.clean_amount(row.get("withdrawal", 0))
                d = self.clean_amount(row.get("deposit", 0))
                if w > 0 and merged_rows[-1]["withdrawal"] == 0:
                    merged_rows[-1]["withdrawal"] = w
                if d > 0 and merged_rows[-1]["deposit"] == 0:
                    merged_rows[-1]["deposit"] = d

        return [t for t in merged_rows if t["date"] and (t["withdrawal"] > 0 or t["deposit"] > 0)]
