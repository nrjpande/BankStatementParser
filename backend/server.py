import os
import io
import re
import uuid
import hashlib
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import xml.etree.ElementTree as ET

from parsers.bank_detector import detect_bank, get_parser
from parsers.pdf_parser import parse_pdf
from services.narration_cleaner import (
    clean_narration, detect_merchant, suggest_ledger, generate_transaction_hash
)
from services.tally_export import generate_tally_xml

load_dotenv()

app = FastAPI(title="Bank2Tally API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
mongo_url = os.environ.get("MONGO_URL")
db_name = os.environ.get("DB_NAME")
client = MongoClient(mongo_url)
db = client[db_name]

# Collections
users_col = db["users"]
statements_col = db["statements"]
transactions_col = db["transactions"]
rules_col = db["mapping_rules"]
ledgers_col = db["master_ledgers"]
upload_jobs_col = db["upload_jobs"]

# Auth
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRY = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

# Ensure indexes
users_col.create_index("email", unique=True)
transactions_col.create_index("statement_id")
transactions_col.create_index("user_id")
rules_col.create_index("user_id")
ledgers_col.create_index("user_id")
upload_jobs_col.create_index("job_id")
statements_col.create_index([("user_id", 1), ("file_hash", 1)])


# --- Models ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = ""

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LedgerUpdate(BaseModel):
    ledger: str
    voucher_type: Optional[str] = None

class BulkLedgerUpdate(BaseModel):
    transaction_ids: list
    ledger: str
    voucher_type: Optional[str] = None

class MappingRuleCreate(BaseModel):
    keyword: str
    ledger: str

class ExportRequest(BaseModel):
    company_name: str = "My Company"
    bank_ledger: str = "Bank Account"

class LedgerCreate(BaseModel):
    name: str
    group: str = ""

class BulkLedgerCreate(BaseModel):
    ledgers: List[dict]

class MarkReadyRequest(BaseModel):
    transaction_ids: List[str] = []
    company_name: str = "My Company"
    bank_ledger: str = "Bank Account"


# --- Auth Helpers ---
def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = users_col.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# --- Background processing ---
def process_upload_job(job_id: str, content: bytes, ext: str, filename: str, user_id: str):
    """Process file upload in background thread."""
    try:
        upload_jobs_col.update_one({"job_id": job_id}, {"$set": {"status": "parsing", "progress": 10}})

        if ext == "pdf":
            df = parse_pdf(content)
        elif ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        if df.empty:
            upload_jobs_col.update_one({"job_id": job_id}, {
                "$set": {"status": "failed", "error": "No data found in file", "progress": 100}
            })
            return

        upload_jobs_col.update_one({"job_id": job_id}, {"$set": {"progress": 30}})

        df.columns = [re.sub(r'\s+', ' ', str(c).replace('\n', ' ')).strip() for c in df.columns]
        bank = detect_bank(df)
        parser = get_parser(bank)
        transactions = parser.parse(df)

        if not transactions:
            upload_jobs_col.update_one({"job_id": job_id}, {
                "$set": {"status": "failed", "error": "Could not parse any transactions from the file", "progress": 100}
            })
            return

        upload_jobs_col.update_one({"job_id": job_id}, {"$set": {"progress": 60}})

        user_rules = list(rules_col.find({"user_id": user_id}, {"_id": 0}))

        statement_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(content).hexdigest()
        statement = {
            "statement_id": statement_id,
            "user_id": user_id,
            "filename": filename,
            "bank_detected": bank,
            "transaction_count": len(transactions),
            "file_hash": file_hash,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        statements_col.insert_one(statement)

        upload_jobs_col.update_one({"job_id": job_id}, {"$set": {"progress": 75}})

        txn_docs = []
        seen_hashes = set()
        for txn in transactions:
            original_desc = txn["description"]
            cleaned_desc = clean_narration(original_desc)
            merchant = detect_merchant(original_desc)
            ledger = suggest_ledger(merchant)

            for rule in user_rules:
                if rule["keyword"].lower() in original_desc.lower():
                    ledger = rule["ledger"]
                    break

            withdrawal = txn.get("withdrawal", 0)
            deposit = txn.get("deposit", 0)
            if withdrawal > 0 and deposit > 0:
                voucher_type = "Contra"
            elif withdrawal > 0:
                voucher_type = "Payment"
            else:
                voucher_type = "Receipt"

            txn_hash = generate_transaction_hash(txn["date"], original_desc, withdrawal or deposit)
            is_duplicate = txn_hash in seen_hashes
            seen_hashes.add(txn_hash)

            txn_id = str(uuid.uuid4())
            txn_docs.append({
                "transaction_id": txn_id,
                "statement_id": statement_id,
                "user_id": user_id,
                "date": txn["date"],
                "description": cleaned_desc,
                "original_description": original_desc,
                "withdrawal": withdrawal,
                "deposit": deposit,
                "balance": txn.get("balance", 0),
                "merchant": merchant,
                "ledger": ledger,
                "voucher_type": voucher_type,
                "is_duplicate": is_duplicate,
                "is_mapped": bool(ledger),
                "sync_status": "none",
            })

        if txn_docs:
            transactions_col.insert_many(txn_docs)

        upload_jobs_col.update_one({"job_id": job_id}, {
            "$set": {
                "status": "completed",
                "progress": 100,
                "statement_id": statement_id,
                "bank_detected": bank,
                "total_transactions": len(txn_docs),
                "auto_mapped": sum(1 for t in txn_docs if t["is_mapped"]),
                "duplicates_found": sum(1 for t in txn_docs if t["is_duplicate"]),
            }
        })

    except Exception as e:
        upload_jobs_col.update_one({"job_id": job_id}, {
            "$set": {"status": "failed", "error": str(e), "progress": 100}
        })


# --- Health ---
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Bank2Tally API"}


# --- Auth Routes ---
@app.post("/api/auth/register")
def register(req: RegisterRequest):
    existing = users_col.find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    users_col.insert_one({
        "user_id": user_id,
        "email": req.email,
        "name": req.name,
        "password_hash": pwd_context.hash(req.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Seed default ledgers for new user
    default_ledgers = [
        "Cash", "Bank Account", "Bank Charges", "Office Supplies",
        "Meals & Entertainment", "Travel & Conveyance", "Telephone Charges",
        "Electricity Charges", "Rent", "Salary", "EMI Payments",
        "Insurance", "Vehicle Running", "Subscriptions", "Professional Fees",
        "Printing & Stationery", "Repairs & Maintenance", "Marketing & Advertising",
        "Interest Received", "Interest Paid", "Commission", "Discount",
        "Suspense", "Capital Account", "Drawings", "Loans & Advances",
        "Sundry Debtors", "Sundry Creditors", "GST Input", "GST Output",
        "TDS Receivable", "TDS Payable", "Miscellaneous Expenses",
    ]
    ledger_docs = [{
        "ledger_id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "group": "",
        "source": "default",
    } for name in default_ledgers]
    ledgers_col.insert_many(ledger_docs)

    token = create_token(user_id, req.email)
    return {"token": token, "user": {"user_id": user_id, "email": req.email, "name": req.name}}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = users_col.find_one({"email": req.email})
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["user_id"], user["email"])
    return {
        "token": token,
        "user": {"user_id": user["user_id"], "email": user["email"], "name": user.get("name", "")}
    }


@app.get("/api/auth/me")
def get_me(user=Depends(get_current_user)):
    return user


# --- Upload & Parse (Async with job polling) ---
@app.post("/api/upload")
async def upload_statement(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ("xlsx", "xls", "csv", "pdf"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use .xlsx, .xls, .csv, or .pdf")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 50MB.")

    # Duplicate file check (SHA-256 hash)
    file_hash = hashlib.sha256(content).hexdigest()
    existing = statements_col.find_one({"user_id": user["user_id"], "file_hash": file_hash})
    if existing:
        return {
            "job_id": None,
            "status": "duplicate",
            "message": f"Duplicate file skipped. This file was already uploaded as '{existing['filename']}' on {existing['uploaded_at'][:10]}.",
            "existing_statement_id": existing["statement_id"],
        }

    # Create job and process in background
    job_id = str(uuid.uuid4())
    upload_jobs_col.insert_one({
        "job_id": job_id,
        "user_id": user["user_id"],
        "filename": file.filename,
        "status": "processing",
        "progress": 5,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    thread = threading.Thread(
        target=process_upload_job,
        args=(job_id, content, ext, file.filename, user["user_id"]),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id, "status": "processing", "message": "Upload started. Poll /api/upload/status/{job_id} for progress."}


@app.get("/api/upload/status/{job_id}")
def upload_status(job_id: str, user=Depends(get_current_user)):
    job = upload_jobs_col.find_one({"job_id": job_id, "user_id": user["user_id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# --- Statements ---
@app.get("/api/statements")
def list_statements(user=Depends(get_current_user)):
    stmts = list(statements_col.find({"user_id": user["user_id"]}, {"_id": 0}).sort("uploaded_at", -1).limit(100))
    return stmts


@app.delete("/api/statements/{statement_id}")
def delete_statement(statement_id: str, user=Depends(get_current_user)):
    result = statements_col.delete_one({"statement_id": statement_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Statement not found")
    transactions_col.delete_many({"statement_id": statement_id})
    return {"message": "Statement deleted"}


# --- Transactions ---
@app.get("/api/transactions/{statement_id}")
def get_transactions(statement_id: str, user=Depends(get_current_user)):
    txns = list(transactions_col.find(
        {"statement_id": statement_id, "user_id": user["user_id"]},
        {"_id": 0}
    ).limit(10000))
    return txns


@app.put("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: str, update: LedgerUpdate, user=Depends(get_current_user)):
    update_data = {"ledger": update.ledger, "is_mapped": bool(update.ledger)}
    if update.voucher_type:
        update_data["voucher_type"] = update.voucher_type

    result = transactions_col.update_one(
        {"transaction_id": transaction_id, "user_id": user["user_id"]},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Updated"}


@app.put("/api/transactions/bulk/update")
def bulk_update_transactions(update: BulkLedgerUpdate, user=Depends(get_current_user)):
    update_data = {"ledger": update.ledger, "is_mapped": bool(update.ledger)}
    if update.voucher_type:
        update_data["voucher_type"] = update.voucher_type

    result = transactions_col.update_many(
        {"transaction_id": {"$in": update.transaction_ids}, "user_id": user["user_id"]},
        {"$set": update_data}
    )
    return {"matched": result.matched_count, "modified": result.modified_count}


# --- Mapping Rules ---
@app.get("/api/mapping-rules")
def get_rules(user=Depends(get_current_user)):
    rules = list(rules_col.find({"user_id": user["user_id"]}, {"_id": 0}).limit(1000))
    return rules


@app.post("/api/mapping-rules")
def create_rule(rule: MappingRuleCreate, user=Depends(get_current_user)):
    existing = rules_col.find_one({"user_id": user["user_id"], "keyword": rule.keyword.lower()})
    if existing:
        rules_col.update_one(
            {"user_id": user["user_id"], "keyword": rule.keyword.lower()},
            {"$set": {"ledger": rule.ledger}}
        )
        return {"message": "Rule updated", "rule_id": existing.get("rule_id", "")}

    rule_id = str(uuid.uuid4())
    rules_col.insert_one({
        "rule_id": rule_id,
        "user_id": user["user_id"],
        "keyword": rule.keyword.lower(),
        "ledger": rule.ledger,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"message": "Rule created", "rule_id": rule_id}


@app.delete("/api/mapping-rules/{rule_id}")
def delete_rule(rule_id: str, user=Depends(get_current_user)):
    result = rules_col.delete_one({"rule_id": rule_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}


@app.post("/api/apply-rules/{statement_id}")
def apply_rules(statement_id: str, user=Depends(get_current_user)):
    rules = list(rules_col.find({"user_id": user["user_id"]}, {"_id": 0}).limit(1000))
    if not rules:
        return {"message": "No rules to apply", "updated": 0}

    txns = list(transactions_col.find(
        {"statement_id": statement_id, "user_id": user["user_id"]},
        {"_id": 0}
    ).limit(10000))

    updated = 0
    for txn in txns:
        desc = txn.get("original_description", txn.get("description", "")).lower()
        for rule in rules:
            if rule["keyword"].lower() in desc:
                transactions_col.update_one(
                    {"transaction_id": txn["transaction_id"]},
                    {"$set": {"ledger": rule["ledger"], "is_mapped": True}}
                )
                updated += 1
                break

    return {"message": f"Applied rules to {updated} transactions", "updated": updated}


# --- Master Ledgers (DB-backed) ---
@app.get("/api/ledgers")
def get_ledgers(user=Depends(get_current_user)):
    ledger_docs = list(ledgers_col.find({"user_id": user["user_id"]}, {"_id": 0}).sort("name", 1).limit(5000))
    return ledger_docs


@app.get("/api/ledgers/names")
def get_ledger_names(user=Depends(get_current_user)):
    """Simple list of ledger names for dropdowns."""
    names = ledgers_col.distinct("name", {"user_id": user["user_id"]})
    return sorted(names)


@app.post("/api/ledgers")
def create_ledger(ledger: LedgerCreate, user=Depends(get_current_user)):
    existing = ledgers_col.find_one({"user_id": user["user_id"], "name": ledger.name})
    if existing:
        raise HTTPException(status_code=400, detail="Ledger already exists")

    ledger_id = str(uuid.uuid4())
    ledgers_col.insert_one({
        "ledger_id": ledger_id,
        "user_id": user["user_id"],
        "name": ledger.name,
        "group": ledger.group,
        "source": "manual",
    })
    return {"message": "Ledger created", "ledger_id": ledger_id}


@app.delete("/api/ledgers/{ledger_id}")
def delete_ledger(ledger_id: str, user=Depends(get_current_user)):
    result = ledgers_col.delete_one({"ledger_id": ledger_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return {"message": "Ledger deleted"}


@app.post("/api/ledgers/import-tally-xml")
async def import_tally_xml(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Import ledgers from a Tally Master XML file."""
    content = await file.read()
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        raise HTTPException(status_code=400, detail="Invalid XML file")

    ledger_names = set()
    # Try various Tally XML structures
    for tag in ["LEDGER", "STOCKITEM", "COSTCENTRE"]:
        for elem in root.iter(tag):
            name = elem.get("NAME") or elem.findtext("NAME") or elem.findtext("LEDGERNAME")
            if name:
                ledger_names.add(name.strip())

    # Also try ALLLEDGERENTRIES
    for entry in root.iter("ALLLEDGERENTRIES.LIST"):
        name = entry.findtext("LEDGERNAME")
        if name:
            ledger_names.add(name.strip())

    # Also try direct LEDGERNAME tags
    for elem in root.iter("LEDGERNAME"):
        if elem.text:
            ledger_names.add(elem.text.strip())

    # Broader: any element with NAME attribute in TALLYMESSAGE
    for msg in root.iter("TALLYMESSAGE"):
        for child in msg:
            name = child.get("NAME")
            if name:
                ledger_names.add(name.strip())

    if not ledger_names:
        raise HTTPException(status_code=400, detail="No ledgers found in the XML file")

    existing_names = set(ledgers_col.distinct("name", {"user_id": user["user_id"]}))
    new_ledgers = ledger_names - existing_names

    if new_ledgers:
        docs = [{
            "ledger_id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "name": name,
            "group": "",
            "source": "tally_import",
        } for name in new_ledgers]
        ledgers_col.insert_many(docs)

    return {
        "message": f"Imported {len(new_ledgers)} new ledgers ({len(ledger_names - new_ledgers)} already existed)",
        "imported": len(new_ledgers),
        "skipped": len(ledger_names - new_ledgers),
        "total_in_file": len(ledger_names),
    }


# --- Tally Sync (Mark as Ready + Fetch pending) ---
@app.post("/api/tally/mark-ready/{statement_id}")
def mark_ready_for_tally(statement_id: str, req: MarkReadyRequest = Body(default=MarkReadyRequest()), user=Depends(get_current_user)):
    query = {"statement_id": statement_id, "user_id": user["user_id"], "is_mapped": True}
    if req.transaction_ids:
        query["transaction_id"] = {"$in": req.transaction_ids}

    result = transactions_col.update_many(query, {
        "$set": {
            "sync_status": "pending_sync",
            "sync_company": req.company_name,
            "sync_bank_ledger": req.bank_ledger,
            "sync_marked_at": datetime.now(timezone.utc).isoformat(),
        }
    })
    return {"message": f"Marked {result.modified_count} transactions as ready for Tally sync", "count": result.modified_count}


@app.get("/api/tally/pending")
def get_pending_sync(user=Depends(get_current_user)):
    """Fetch transactions pending Tally sync. Used by the local tally_agent."""
    txns = list(transactions_col.find(
        {"user_id": user["user_id"], "sync_status": "pending_sync"},
        {"_id": 0}
    ).limit(10000))
    return txns


@app.post("/api/tally/confirm-sync")
def confirm_sync(transaction_ids: List[str] = Body(...), user=Depends(get_current_user)):
    """Mark transactions as synced after local tally_agent pushes them."""
    result = transactions_col.update_many(
        {"transaction_id": {"$in": transaction_ids}, "user_id": user["user_id"]},
        {"$set": {"sync_status": "synced", "synced_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"synced": result.modified_count}


# --- Export XML (kept for backward compat) ---
@app.post("/api/export/tally/{statement_id}")
def export_tally(statement_id: str, req: ExportRequest = Body(default=ExportRequest()), user=Depends(get_current_user)):
    txns = list(transactions_col.find(
        {"statement_id": statement_id, "user_id": user["user_id"]},
        {"_id": 0}
    ).limit(10000))

    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found")

    for txn in txns:
        txn["bank_ledger"] = req.bank_ledger

    xml_content = generate_tally_xml(txns, req.company_name)

    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=tally_export_{statement_id[:8]}.xml"}
    )


# --- Dashboard Stats ---
@app.get("/api/dashboard/stats")
def dashboard_stats(user=Depends(get_current_user)):
    total_statements = statements_col.count_documents({"user_id": user["user_id"]})
    total_transactions = transactions_col.count_documents({"user_id": user["user_id"]})
    mapped_transactions = transactions_col.count_documents({"user_id": user["user_id"], "is_mapped": True})
    total_rules = rules_col.count_documents({"user_id": user["user_id"]})
    pending_sync = transactions_col.count_documents({"user_id": user["user_id"], "sync_status": "pending_sync"})
    synced = transactions_col.count_documents({"user_id": user["user_id"], "sync_status": "synced"})

    pipeline = [
        {"$match": {"user_id": user["user_id"]}},
        {"$limit": 100000},
        {"$group": {
            "_id": None,
            "total_withdrawals": {"$sum": "$withdrawal"},
            "total_deposits": {"$sum": "$deposit"},
        }}
    ]
    agg_result = list(transactions_col.aggregate(pipeline))
    totals = agg_result[0] if agg_result else {"total_withdrawals": 0, "total_deposits": 0}

    recent = list(statements_col.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("uploaded_at", -1).limit(5))

    ledger_pipeline = [
        {"$match": {"user_id": user["user_id"], "ledger": {"$ne": ""}}},
        {"$group": {"_id": "$ledger", "count": {"$sum": 1}, "total": {"$sum": {"$add": ["$withdrawal", "$deposit"]}}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    ledger_dist = list(transactions_col.aggregate(ledger_pipeline))
    ledger_distribution = [{"ledger": d["_id"], "count": d["count"], "total": d["total"]} for d in ledger_dist]

    return {
        "total_statements": total_statements,
        "total_transactions": total_transactions,
        "mapped_transactions": mapped_transactions,
        "unmapped_transactions": total_transactions - mapped_transactions,
        "total_rules": total_rules,
        "pending_sync": pending_sync,
        "synced": synced,
        "total_withdrawals": totals.get("total_withdrawals", 0),
        "total_deposits": totals.get("total_deposits", 0),
        "recent_statements": recent,
        "ledger_distribution": ledger_distribution,
    }
