import pandas as pd
import re
from datetime import datetime


class BaseParser:
    bank_name = "Unknown"

    def clean_amount(self, value) -> float:
        if pd.isna(value) or value is None or str(value).strip() == "":
            return 0.0
        s = str(value).replace(",", "").replace("₹", "").replace("$", "").replace("INR", "").strip()
        s = re.sub(r'[^\d.\-]', '', s)
        try:
            return abs(float(s))
        except (ValueError, TypeError):
            return 0.0

    def clean_date(self, value) -> str:
        if pd.isna(value) or value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d")

        s = str(value).strip()
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
            "%Y-%m-%d", "%m/%d/%Y", "%d %b %Y", "%d %B %Y",
            "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
            "%d-%b-%Y", "%d-%b-%y", "%d %b %y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return s

    def clean_description(self, value) -> str:
        if pd.isna(value) or value is None:
            return ""
        return str(value).strip()

    def detect_header_row(self, df: pd.DataFrame, keywords: list) -> int:
        for idx, row in df.iterrows():
            row_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
            match_count = sum(1 for kw in keywords if kw.lower() in row_str)
            if match_count >= 2:
                return idx
        return 0

    def parse(self, df: pd.DataFrame) -> list:
        raise NotImplementedError

    def to_standard_format(self, df: pd.DataFrame) -> list:
        transactions = []
        for _, row in df.iterrows():
            txn = {
                "date": self.clean_date(row.get("date", "")),
                "description": self.clean_description(row.get("description", "")),
                "withdrawal": self.clean_amount(row.get("withdrawal", 0)),
                "deposit": self.clean_amount(row.get("deposit", 0)),
                "balance": self.clean_amount(row.get("balance", 0)),
            }
            if txn["date"] and (txn["withdrawal"] > 0 or txn["deposit"] > 0):
                transactions.append(txn)
        return transactions
