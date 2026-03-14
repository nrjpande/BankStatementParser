# Bank2Tally - Product Requirements Document

## Original Problem Statement
Build a bank statement to Tally automation SaaS app (like Suvit). Upload bank statements (Excel/CSV/PDF), parse transactions, show in editable AG Grid table, allow ledger mapping with auto-mapping rules, and export to Tally XML. Target users: Chartered Accountants, Accounting Firms.

## Architecture
- **Frontend**: React + AG Grid v35 + Tailwind CSS + Recharts
- **Backend**: FastAPI (Python) + MongoDB
- **Auth**: JWT-based email/password
- **Parser Engine**: HDFC, ICICI, SBI, Axis, Kotak, Generic parsers
- **AI Cleaning**: Rule-based narration cleaner + merchant dictionary

## User Personas
1. **Chartered Accountant** — Processes 10-50 bank statements/month for clients
2. **Accounting Firm Staff** — Bulk processes statements, needs auto-mapping
3. **Business Owner** — Imports own bank data to Tally monthly

## Core Requirements (Static)
- Upload Excel/CSV/PDF bank statements
- Auto-detect bank format (HDFC, ICICI, SBI, Axis, Kotak, Generic)
- Parse & normalize transactions to standard format
- AI narration cleaning (rule-based regex + merchant dictionary)
- Merchant detection from descriptions
- Editable AG Grid transaction table
- Ledger mapping (dropdown with 30+ standard ledgers)
- Auto-mapping rules engine (keyword -> ledger)
- Bulk ledger assignment
- Voucher type auto-detection (Payment/Receipt/Contra)
- Duplicate transaction detection
- Tally XML export/download
- Dashboard with stats & charts
- JWT authentication

## What's Been Implemented (March 14, 2026)
### Backend (100% API tests passing)
- [x] Auth: Register, Login, Get Current User
- [x] File Upload & Parse (Excel, CSV, PDF)
- [x] Bank Detection (HDFC, ICICI, SBI, Axis, Kotak, Generic)
- [x] Narration Cleaning Engine
- [x] Merchant Detection (40+ merchants)
- [x] Auto Ledger Suggestion
- [x] Transaction CRUD (single + bulk update)
- [x] Mapping Rules CRUD
- [x] Apply Rules to Statement
- [x] Tally XML Export (valid TallyPrime import format)
- [x] Dashboard Statistics API
- [x] Ledger List API (30+ standard ledgers)

### Frontend (90%+ tests passing)
- [x] Login/Register pages with split layout
- [x] Sidebar navigation (Dashboard, Upload, Statements, Rules)
- [x] Dashboard with stat cards, bar chart, pie chart, recent statements
- [x] Upload page with drag-drop zone
- [x] Statements list page
- [x] Transaction table with AG Grid v35 (editable, sortable, filterable)
- [x] Bulk actions (select multiple -> assign ledger)
- [x] Mapping Rules page (create, list, delete)
- [x] Tally XML export button

## Prioritized Backlog

### P0 (Critical - Next Sprint)
- CSV file upload testing
- PDF file upload testing
- Push to Tally endpoint (localhost:9000)

### P1 (Important)
- Dark mode toggle
- Multi-statement merge
- Reconciliation checks (opening/closing balance validation)
- Custom ledger creation from transaction table
- Rule auto-creation when mapping in table

### P2 (Nice to Have)
- AI-powered narration cleaning (LLM integration)
- ML auto-classification
- Import ledgers from Tally
- GST classification (IGST/CGST/SGST)
- Export to CSV/JSON/PDF report
- Multi-currency support
- User settings page
- Team/multi-user support
- Undo/redo functionality

## Next Tasks
1. Test CSV and PDF parsing end-to-end
2. Add Push to Tally functionality
3. Add dark mode
4. Custom ledger creation from UI
5. Build reconciliation checks
