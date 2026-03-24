# Bank2Tally - Product Requirements Document

## Original Problem Statement
Build a bank statement to Tally automation SaaS app (like Suvit). Upload bank statements (Excel/CSV/PDF), parse transactions, show in editable AG Grid table, allow ledger mapping with auto-mapping rules, and export to Tally XML.

## Architecture
- **Frontend**: React + AG Grid v35 + Tailwind CSS + Recharts
- **Backend**: FastAPI (Python) + MongoDB
- **Auth**: JWT-based email/password
- **Parser Engine**: HDFC, ICICI, SBI, Axis, Kotak, Generic parsers + PDF text extraction
- **AI Cleaning**: Rule-based narration cleaner + merchant dictionary
- **Tally Bridge**: Cloud mark-ready + standalone local tally_agent.py

## What's Been Implemented (March 24, 2026)

### Backend
- [x] JWT Auth (Register/Login) with default ledger seeding
- [x] **Async file upload** with background processing + job polling
- [x] **50MB file size limit** (up from 20MB)
- [x] **SHA-256 duplicate file detection** — skips re-uploading same files
- [x] Bank Detection (HDFC, ICICI, SBI, Axis, Kotak, DBS, IDFC, AU Small, BOI, Generic)
- [x] PDF parsing — table extraction + text-based fallback + multi-line cell handling
- [x] Excel/CSV parsing (.xlsx, .xls via xlrd, .csv)
- [x] Narration Cleaning + Merchant Detection (40+ merchants)
- [x] Auto Ledger Suggestion + User Mapping Rules
- [x] **DB-backed Master Ledgers** (CRUD + Import from Tally XML)
- [x] **Tally Sync workflow** — Mark Ready → Pending → Synced
- [x] Standalone tally_agent.py for local Tally push
- [x] Dashboard Statistics with sync status counts
- [x] Transaction CRUD (single + bulk update)

### Frontend
- [x] Login/Register with split layout
- [x] Dashboard with charts + stats
- [x] **Async Upload page** with job polling progress bar + duplicate detection
- [x] Statements list page
- [x] **Transaction Table** — Serial # column, single checkbox, no blank columns
- [x] **Advanced Filter Panel** — Date range, Type, Keyword, Mapped/Unmapped, Clear All
- [x] **Dynamic KPI Cards** — Total Debits, Credits, Net + Filtered Subtotals
- [x] **"Mark as Ready for Tally"** button (replaces XML download)
- [x] **Sync status indicator** column in grid
- [x] **Master Ledgers page** — Add/Delete/Search + Import from Tally XML
- [x] Mapping Rules page (uses DB-backed ledgers)
- [x] Sidebar navigation with 5 sections

### PDF Parsing Tested
| PDF | Bank | Transactions |
|-----|------|-------------|
| DBS.pdf | DBS | 23 |
| IDFC.pdf | IDFC First | 85 |
| AU_SMALL.pdf | AU Small Finance | 181 |
| HDFC_SA.pdf | HDFC Savings | 4 |
| BOI.pdf | BOI | Password-protected (error handled) |

### Standalone Script
- [x] `/app/tally_agent.py` — Polls cloud API, builds Tally XML, pushes to localhost:9000

## Prioritized Backlog

### P0 (Next)
- Password-protected PDF support (user provides password)
- CSV file parsing validation with real files
- More bank PDF formats (Federal, Canara, Union, PNB)

### P1
- Dark mode toggle
- Reconciliation checks (opening/closing balance)
- Custom ledger groups
- Bulk import rules from CSV

### P2
- AI-powered narration cleaning (LLM)
- ML auto-classification
- Multi-statement merge
- GST classification
- User settings page
- Team/multi-user support

## Next Tasks
1. Test with more real bank PDFs
2. Add password-protected PDF handling
3. Build reconciliation checks
4. Dark mode
