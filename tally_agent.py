#!/usr/bin/env python3
"""
Bank2Tally Local Agent
======================
This script runs on your LOCAL machine (where TallyPrime is installed).
It periodically fetches pending transactions from the Bank2Tally cloud app,
converts them to Tally XML, and pushes them directly to your local Tally.

Setup:
  1. pip install requests
  2. Set your credentials below
  3. Run: python tally_agent.py

Requirements:
  - TallyPrime must be running with XML Server enabled on port 9000
  - Internet access to reach your Bank2Tally cloud instance
"""

import requests
import time
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# ============ CONFIGURATION ============
CLOUD_URL = "https://YOUR-APP-URL.preview.emergentagent.com"  # Your Bank2Tally cloud URL
EMAIL = "your@email.com"
PASSWORD = "your_password"
TALLY_URL = "http://localhost:9000"       # Local TallyPrime HTTP endpoint
POLL_INTERVAL = 30                        # Seconds between polling
# =======================================


def login(base_url, email, password):
    """Login to Bank2Tally and get auth token."""
    resp = requests.post(f"{base_url}/api/auth/login", json={
        "email": email, "password": password
    })
    resp.raise_for_status()
    return resp.json()["token"]


def fetch_pending(base_url, token):
    """Fetch transactions marked as pending_sync."""
    resp = requests.get(f"{base_url}/api/tally/pending", headers={
        "Authorization": f"Bearer {token}"
    })
    resp.raise_for_status()
    return resp.json()


def confirm_sync(base_url, token, transaction_ids):
    """Mark transactions as synced after successful Tally push."""
    resp = requests.post(f"{base_url}/api/tally/confirm-sync",
        json=transaction_ids,
        headers={"Authorization": f"Bearer {token}"}
    )
    resp.raise_for_status()
    return resp.json()


def build_tally_xml(transactions, company_name="My Company"):
    """Convert transactions to TallyPrime XML import format."""
    envelope = ET.Element("ENVELOPE")

    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    body = ET.SubElement(envelope, "BODY")
    import_data = ET.SubElement(body, "IMPORTDATA")

    request_desc = ET.SubElement(import_data, "REQUESTDESC")
    ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"

    static_vars = ET.SubElement(request_desc, "STATICVARIABLES")
    ET.SubElement(static_vars, "SVCURRENTCOMPANY").text = company_name

    request_data = ET.SubElement(import_data, "REQUESTDATA")

    for txn in transactions:
        if not txn.get("ledger"):
            continue

        tallymsg = ET.SubElement(request_data, "TALLYMESSAGE", xmlns_UDF="TallyUDF")
        voucher = ET.SubElement(tallymsg, "VOUCHER", REMOTEID="", ACTION="Create")

        # Date
        txn_date = txn.get("date", "")
        try:
            if "-" in txn_date:
                dt = datetime.strptime(txn_date, "%Y-%m-%d")
            else:
                dt = datetime.strptime(txn_date, "%Y%m%d")
            tally_date = dt.strftime("%Y%m%d")
        except (ValueError, TypeError):
            tally_date = txn_date.replace("-", "")

        withdrawal = float(txn.get("withdrawal", 0) or 0)
        deposit = float(txn.get("deposit", 0) or 0)
        is_debit = withdrawal > 0
        amount = withdrawal if is_debit else deposit
        voucher_type = txn.get("voucher_type", "Payment" if is_debit else "Receipt")

        voucher.set("VCHTYPE", voucher_type)

        ET.SubElement(voucher, "DATE").text = tally_date
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        ET.SubElement(voucher, "NARRATION").text = txn.get("description", "")

        bank_ledger = txn.get("sync_bank_ledger", "Bank Account")

        # Bank side
        entry1 = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(entry1, "LEDGERNAME").text = bank_ledger
        ET.SubElement(entry1, "AMOUNT").text = str(amount if is_debit else -amount)
        ET.SubElement(entry1, "ISDEEMEDPOSITIVE").text = "No" if is_debit else "Yes"

        # Party side
        entry2 = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(entry2, "LEDGERNAME").text = txn.get("ledger", "Suspense")
        ET.SubElement(entry2, "AMOUNT").text = str(-amount if is_debit else amount)
        ET.SubElement(entry2, "ISDEEMEDPOSITIVE").text = "Yes" if is_debit else "No"

    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_str += ET.tostring(envelope, encoding="unicode")
    return xml_str


def push_to_tally(tally_url, xml_content):
    """Send XML to local TallyPrime HTTP server."""
    resp = requests.post(tally_url, data=xml_content.encode("utf-8"), headers={
        "Content-Type": "application/xml"
    }, timeout=30)
    return resp.status_code, resp.text


def main():
    print("=" * 50)
    print("  Bank2Tally Local Agent")
    print("=" * 50)
    print(f"  Cloud:  {CLOUD_URL}")
    print(f"  Tally:  {TALLY_URL}")
    print(f"  Poll:   Every {POLL_INTERVAL}s")
    print("=" * 50)

    # Login
    print("\n[*] Logging in...")
    try:
        token = login(CLOUD_URL, EMAIL, PASSWORD)
        print("[+] Login successful")
    except Exception as e:
        print(f"[!] Login failed: {e}")
        sys.exit(1)

    # Main loop
    print(f"\n[*] Watching for pending transactions...\n")
    while True:
        try:
            pending = fetch_pending(CLOUD_URL, token)

            if pending:
                print(f"[*] Found {len(pending)} pending transactions")

                # Group by company
                company = pending[0].get("sync_company", "My Company")
                xml = build_tally_xml(pending, company)

                print(f"[*] Pushing to Tally at {TALLY_URL}...")
                try:
                    status, response = push_to_tally(TALLY_URL, xml)
                    if status == 200:
                        print(f"[+] Tally accepted {len(pending)} entries")
                        ids = [t["transaction_id"] for t in pending]
                        confirm_sync(CLOUD_URL, token, ids)
                        print(f"[+] Marked {len(ids)} as synced")
                    else:
                        print(f"[!] Tally returned status {status}: {response[:200]}")
                except requests.ConnectionError:
                    print(f"[!] Cannot connect to Tally at {TALLY_URL}. Is TallyPrime running?")
                except Exception as e:
                    print(f"[!] Tally push error: {e}")
            else:
                print(f"[.] No pending transactions ({datetime.now().strftime('%H:%M:%S')})")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("[*] Token expired, re-logging in...")
                try:
                    token = login(CLOUD_URL, EMAIL, PASSWORD)
                except Exception:
                    print("[!] Re-login failed")
            else:
                print(f"[!] API error: {e}")
        except Exception as e:
            print(f"[!] Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
