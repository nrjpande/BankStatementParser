import pdfplumber
import pandas as pd
import re
import io

# Date patterns to identify transaction start lines
DATE_PATTERNS = [
    re.compile(r'^\d{2}[/-]\d{2}[/-]\d{2,4}'),           # dd/mm/yy or dd/mm/yyyy or dd-mm-yy
    re.compile(r'^\d{2}-[A-Za-z]{3}-\d{2,4}'),            # dd-Mon-yy or dd-Mon-yyyy (10-APR-24)
    re.compile(r'^\d{2}\s+[A-Za-z]{3}\s+\d{2,4}'),        # dd Mon yy
    re.compile(r'^\d{2}-[A-Za-z]{3}-\d{4}'),              # dd-Jan-2025
]

AMOUNT_PATTERN = re.compile(r'[\d,]+\.?\d*')


def _is_date_line(line: str) -> bool:
    line = line.strip()
    return any(p.match(line) for p in DATE_PATTERNS)


def _extract_date(line: str) -> str:
    line = line.strip()
    for p in DATE_PATTERNS:
        m = p.match(line)
        if m:
            return m.group(0)
    return ""


def _parse_amount(s: str) -> float:
    if not s or s.strip() in ("", "-", "0"):
        return 0.0
    s = s.replace(",", "").replace("₹", "").replace("INR", "").strip()
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def _try_table_extraction(pdf) -> pd.DataFrame:
    """Try extracting structured tables from PDF."""
    all_rows = []
    headers = None

    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            for row in table:
                cleaned = [cell.strip() if cell else "" for cell in row]
                if not headers:
                    row_text = " ".join(cleaned).lower()
                    has_date = any(kw in row_text for kw in ["date", "txn date", "transaction"])
                    has_amount = any(kw in row_text for kw in [
                        "debit", "credit", "withdrawal", "deposit", "amount", "dr", "cr"
                    ])
                    if has_date and has_amount:
                        headers = cleaned
                        continue
                if headers and any(c for c in cleaned if c and not c.startswith("*")):
                    # Skip rows that are just separators or empty
                    if not all(c == "" or c.startswith("*") or c == "None" for c in cleaned):
                        all_rows.append(cleaned)

    if headers and all_rows:
        max_cols = len(headers)
        padded = []
        for row in all_rows:
            if len(row) < max_cols:
                row = row + [""] * (max_cols - len(row))
            elif len(row) > max_cols:
                row = row[:max_cols]
            padded.append(row)
        return pd.DataFrame(padded, columns=headers)

    return pd.DataFrame()


def _split_multiline_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Handle HDFC SA-style where multiple transactions are in one cell with newlines."""
    new_rows = []
    for _, row in df.iterrows():
        values = [str(v) if pd.notna(v) else "" for v in row.values]
        # Check if any cell has newlines
        max_lines = max(len(v.split('\n')) for v in values)
        if max_lines > 1:
            split_cols = [v.split('\n') for v in values]
            for li in range(max_lines):
                new_row = []
                for col_vals in split_cols:
                    if li < len(col_vals):
                        new_row.append(col_vals[li].strip())
                    else:
                        new_row.append("")
                new_rows.append(new_row)
        else:
            new_rows.append(values)

    return pd.DataFrame(new_rows, columns=df.columns)


def _text_based_extraction(pdf) -> list:
    """Parse transactions from text when tables fail. Works for DBS, AU Small, BOI, etc."""
    transactions = []

    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.split('\n')
        current_txn = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip header/footer lines
            lower = line.lower()
            if any(skip in lower for skip in [
                "opening balance", "closing balance", "page", "statement",
                "account", "branch", "address", "customer", "ifsc",
                "generated", "computer generated", "disclaimer",
                "end of statement", "total", "summary",
                "private", "confidential", "currency", "important"
            ]):
                # But "opening balance" with a number might be data
                if "opening balance" in lower or "closing balance" in lower:
                    continue
                if _is_date_line(line):
                    pass  # It's a transaction line that happens to contain a keyword
                else:
                    continue

            if _is_date_line(line):
                # Save previous transaction
                if current_txn and current_txn.get("date"):
                    transactions.append(current_txn)

                # Parse new transaction from this line
                date_str = _extract_date(line)
                rest = line[len(date_str):].strip()

                # Check for second date (Value Date) and skip it
                if _is_date_line(rest):
                    second_date = _extract_date(rest)
                    rest = rest[len(second_date):].strip()

                # Try to extract amounts from the right side
                # Pattern: description ... amount1 amount2 balance
                parts = rest.split()
                right_amounts = []
                temp_parts = list(parts)
                while temp_parts:
                    last = temp_parts[-1]
                    cleaned_last = last.replace(",", "").replace(".", "").replace("-", "")
                    if cleaned_last.isdigit():
                        right_amounts.insert(0, last)
                        temp_parts.pop()
                    else:
                        break

                desc_parts = temp_parts
                description = " ".join(desc_parts)

                # Parse amounts
                debit = 0.0
                credit = 0.0
                balance = 0.0

                if len(right_amounts) >= 3:
                    debit = _parse_amount(right_amounts[0])
                    credit = _parse_amount(right_amounts[1])
                    balance = _parse_amount(right_amounts[2])
                elif len(right_amounts) == 2:
                    amt1 = _parse_amount(right_amounts[0])
                    amt2 = _parse_amount(right_amounts[1])
                    if amt2 >= amt1:
                        balance = amt2
                        debit = amt1
                    else:
                        balance = amt1
                        credit = amt2
                elif len(right_amounts) == 1:
                    balance = _parse_amount(right_amounts[0])

                current_txn = {
                    "date": date_str,
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": balance,
                }
            elif current_txn:
                # Continuation line - append to description
                current_txn["description"] += " " + line

        # Don't forget the last transaction
        if current_txn and current_txn.get("date"):
            transactions.append(current_txn)

    return transactions


def _text_extraction_to_df(transactions: list) -> pd.DataFrame:
    """Convert text-extracted transactions to a DataFrame matching our standard format."""
    if not transactions:
        return pd.DataFrame()

    rows = []
    for txn in transactions:
        rows.append({
            "Date": txn.get("date", ""),
            "Description": txn.get("description", "").strip(),
            "Withdrawal": txn.get("debit", 0),
            "Deposit": txn.get("credit", 0),
            "Balance": txn.get("balance", 0),
        })

    return pd.DataFrame(rows)


def parse_pdf(file_bytes: bytes) -> pd.DataFrame:
    """Main PDF parser. Tries table extraction first, falls back to text-based."""
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            raise ValueError("This PDF is password-protected. Please remove the password and try again.")
        raise ValueError(f"Could not open PDF: {str(e)}")

    try:
        # Method 1: Try structured table extraction
        df = _try_table_extraction(pdf)

        if not df.empty:
            # Quality check: if most rows have data only in column 0, table extraction is bad
            if len(df.columns) > 2 and len(df) > 3:
                bad_cols = 0
                for col in df.columns[1:]:
                    col_data = df[col].astype(str).replace('None', '').replace('nan', '').str.strip()
                    empty_pct = (col_data == '').sum() / len(df)
                    if empty_pct > 0.7:  # >70% empty means this column is bad
                        bad_cols += 1
                if bad_cols >= len(df.columns) - 2:
                    # Bad table - all data crammed into first column, fall back to text
                    df = pd.DataFrame()

        if not df.empty:
            # Check if tables have multi-line cells that need splitting
            for col in df.columns:
                if df[col].astype(str).str.contains('\n').any():
                    df = _split_multiline_cells(df)
                    break

            # Validate we got actual transaction data
            col_text = " ".join(str(c).lower() for c in df.columns)
            has_date_col = any(kw in col_text for kw in ["date", "txn"])
            has_amount_col = any(kw in col_text for kw in [
                "debit", "credit", "withdrawal", "deposit", "dr", "cr", "amount"
            ])
            if has_date_col and has_amount_col and len(df) > 0:
                return df

        # Method 2: Text-based extraction
        text_txns = _text_based_extraction(pdf)
        if text_txns:
            return _text_extraction_to_df(text_txns)

        # Method 3: If table extraction returned something but without proper headers
        if not df.empty:
            return df

        return pd.DataFrame()
    finally:
        pdf.close()
