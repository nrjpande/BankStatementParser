import xml.etree.ElementTree as ET
from datetime import datetime


def generate_tally_xml(transactions: list, company_name: str = "My Company") -> str:
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
        voucher = ET.SubElement(tallymsg, "VOUCHER", REMOTEID="", VCHTYPE="", ACTION="Create")

        txn_date = txn.get("date", "")
        try:
            if "-" in txn_date:
                dt = datetime.strptime(txn_date, "%Y-%m-%d")
            elif "/" in txn_date:
                dt = datetime.strptime(txn_date, "%d/%m/%Y")
            else:
                dt = datetime.strptime(txn_date, "%Y%m%d")
            tally_date = dt.strftime("%Y%m%d")
        except (ValueError, TypeError):
            tally_date = txn_date.replace("-", "")

        withdrawal = float(txn.get("withdrawal", 0) or 0)
        deposit = float(txn.get("deposit", 0) or 0)

        if withdrawal > 0:
            voucher_type = txn.get("voucher_type", "Payment")
            amount = withdrawal
            is_debit = True
        else:
            voucher_type = txn.get("voucher_type", "Receipt")
            amount = deposit
            is_debit = False

        voucher.set("VCHTYPE", voucher_type)

        ET.SubElement(voucher, "DATE").text = tally_date
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        ET.SubElement(voucher, "NARRATION").text = txn.get("description", "")

        # Bank ledger entry
        bank_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(bank_entry, "LEDGERNAME").text = txn.get("bank_ledger", "Bank Account")
        if is_debit:
            ET.SubElement(bank_entry, "AMOUNT").text = str(amount)
        else:
            ET.SubElement(bank_entry, "AMOUNT").text = str(-amount)
        ET.SubElement(bank_entry, "ISDEEMEDPOSITIVE").text = "No" if is_debit else "Yes"

        # Party ledger entry
        party_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(party_entry, "LEDGERNAME").text = txn.get("ledger", "Suspense")
        if is_debit:
            ET.SubElement(party_entry, "AMOUNT").text = str(-amount)
        else:
            ET.SubElement(party_entry, "AMOUNT").text = str(amount)
        ET.SubElement(party_entry, "ISDEEMEDPOSITIVE").text = "Yes" if is_debit else "No"

    tree = ET.ElementTree(envelope)
    ET.indent(tree, space="  ")

    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_str = ET.tostring(envelope, encoding="unicode")

    return xml_declaration + xml_str
