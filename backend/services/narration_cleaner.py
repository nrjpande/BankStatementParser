import re
import hashlib


NOISE_TOKENS = [
    "upi", "neft", "imps", "rtgs", "ecs", "nach", "dr", "cr", "ref", "txn",
    "inb", "mob", "ib", "mb", "bil", "bpay", "ach", "cms", "mmt", "fund",
    "transfer", "trf", "payment", "received", "from", "to", "by", "via",
    "being", "towards", "for", "the", "and", "a", "an"
]

MERCHANT_DICTIONARY = {
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "uber": "Uber",
    "ola": "Ola",
    "paytm": "Paytm",
    "phonepe": "PhonePe",
    "google pay": "Google Pay",
    "gpay": "Google Pay",
    "netflix": "Netflix",
    "hotstar": "Hotstar",
    "spotify": "Spotify",
    "airtel": "Airtel",
    "jio": "Jio",
    "vodafone": "Vodafone",
    "bsnl": "BSNL",
    "electricity": "Electricity",
    "water bill": "Water Bill",
    "rent": "Rent",
    "salary": "Salary",
    "emi": "EMI",
    "insurance": "Insurance",
    "mutual fund": "Mutual Fund",
    "sip": "SIP",
    "atm": "ATM",
    "cash": "Cash",
    "petrol": "Petrol",
    "diesel": "Diesel",
    "hp petrol": "HP Petrol",
    "bpcl": "BPCL",
    "iocl": "IOCL",
    "bigbasket": "BigBasket",
    "dmart": "DMart",
    "reliance": "Reliance",
    "myntra": "Myntra",
    "zepto": "Zepto",
    "blinkit": "Blinkit",
    "dunzo": "Dunzo",
    "makemytrip": "MakeMyTrip",
    "irctc": "IRCTC",
    "dominos": "Dominos",
    "mcdonalds": "McDonalds",
    "starbucks": "Starbucks",
    "hdfc": "HDFC",
    "icici": "ICICI",
    "sbi": "SBI",
    "axis": "Axis",
    "kotak": "Kotak",
}

DEFAULT_LEDGER_MAP = {
    "Swiggy": "Meals & Entertainment",
    "Zomato": "Meals & Entertainment",
    "Amazon": "Office Supplies",
    "Flipkart": "Office Supplies",
    "Uber": "Travel & Conveyance",
    "Ola": "Travel & Conveyance",
    "Netflix": "Subscriptions",
    "Hotstar": "Subscriptions",
    "Spotify": "Subscriptions",
    "Airtel": "Telephone Charges",
    "Jio": "Telephone Charges",
    "Vodafone": "Telephone Charges",
    "Electricity": "Electricity Charges",
    "Rent": "Rent",
    "Salary": "Salary",
    "EMI": "EMI Payments",
    "Insurance": "Insurance",
    "ATM": "Cash",
    "Cash": "Cash",
    "Petrol": "Vehicle Running",
    "HP Petrol": "Vehicle Running",
    "BPCL": "Vehicle Running",
    "IOCL": "Vehicle Running",
}


def clean_narration(text: str) -> str:
    if not text or not isinstance(text, str):
        return str(text) if text else ""

    cleaned = text.lower().strip()
    cleaned = re.sub(r'[/\-_|\\]', ' ', cleaned)
    cleaned = re.sub(r'\d{6,}', '', cleaned)
    cleaned = re.sub(r'\b\d{3,5}\b', '', cleaned)

    for token in NOISE_TOKENS:
        cleaned = re.sub(r'\b' + re.escape(token) + r'\b', '', cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if cleaned:
        cleaned = cleaned.title()

    return cleaned if cleaned else text.strip()


def detect_merchant(description: str) -> str:
    if not description:
        return ""
    desc_lower = description.lower()
    for keyword, merchant in MERCHANT_DICTIONARY.items():
        if keyword in desc_lower:
            return merchant
    return ""


def suggest_ledger(merchant: str) -> str:
    if not merchant:
        return ""
    return DEFAULT_LEDGER_MAP.get(merchant, "")


def generate_transaction_hash(date: str, description: str, amount: float) -> str:
    raw = f"{date}|{description}|{amount}"
    return hashlib.md5(raw.encode()).hexdigest()
