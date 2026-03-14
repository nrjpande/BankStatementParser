import pdfplumber
import pandas as pd
import io


def parse_pdf(file_bytes: bytes) -> pd.DataFrame:
    all_rows = []
    headers = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    cleaned = [cell.strip() if cell else "" for cell in row]
                    if not headers:
                        # Check if this looks like a header
                        row_text = " ".join(cleaned).lower()
                        if "date" in row_text and ("debit" in row_text or "credit" in row_text or "amount" in row_text or "withdrawal" in row_text or "deposit" in row_text):
                            headers = cleaned
                            continue
                    if headers and any(c for c in cleaned):
                        all_rows.append(cleaned)

    if not headers and all_rows:
        headers = all_rows[0]
        all_rows = all_rows[1:]

    if headers and all_rows:
        # Ensure all rows have same length as headers
        max_cols = len(headers)
        padded_rows = []
        for row in all_rows:
            if len(row) < max_cols:
                row = row + [""] * (max_cols - len(row))
            elif len(row) > max_cols:
                row = row[:max_cols]
            padded_rows.append(row)
        return pd.DataFrame(padded_rows, columns=headers)

    return pd.DataFrame()
