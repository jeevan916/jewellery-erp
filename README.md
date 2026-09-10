# Jewellery ERP

Production-oriented, online-only jewellery ERP for Indian jewellery retail and accounting.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Django + Django REST Framework
- Database: MySQL / InnoDB
- Authentication: DRF token authentication
- Deployment target: Hostinger (later)

## Current runnable workflow

Dashboard → Customers → Sales Invoice → Post → Receipt → Outstanding → Ledger → Trial Balance / P&L / Balance Sheet.

Accounting is server-side and journal-derived. Bill-wise allocations are append-only: corrections use deallocation/reallocation rather than deleting financial history.

## Local Windows setup

### 1. MySQL

Create a database named `jewellery_erp` in MySQL/XAMPP and make sure MySQL is listening on port 3306.

Set environment variables if your local credentials differ:

```powershell
$env:MYSQL_DATABASE="jewellery_erp"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD=""
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py check
python manage.py test
python manage.py runserver
```

Demo login: `admin` / `admin`.

API: `http://127.0.0.1:8000/api/accounting/`

### 3. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173/`.

If the backend uses another URL, set `VITE_API_URL` before `npm run dev`.

## API endpoints

- `POST /auth/login/`
- `GET /dashboard/`
- `GET|POST /parties/`
- `GET /accounts/`
- `GET /periods/`
- `GET|POST /invoices/`
- `POST /invoices/:id/post/`
- `GET|POST /payments/`
- `POST /payments/:id/post/`
- `GET|POST /allocations/`
- `POST /allocations/:id/deallocate/`
- `GET /outstanding/`
- `GET /ledger/:account_id/`
- `GET /reports/trial-balance/`
- `GET /reports/profit-loss/`
- `GET /reports/balance-sheet/`

## Accounting integrity

Posted vouchers are balanced inside atomic transactions. Ledgers and financial reports are calculated from posted journal lines. Customer receipts and supplier payments support partial and multi-bill allocation, overpayment/unallocated balances, and append-only deallocation.

## Production direction

The local stack is intentionally deployment-agnostic. Later the same Django application can use Hostinger MySQL and the React build can be served through the production web stack. No offline-first or local accounting database is used.

## Important

This repository now contains a **runnable accounting MVP**, not the final production-complete jewellery ERP. Inventory, HUID/lot controls, GST filing workflows, bank/POS statement ingestion, OCR document inbox, gateway settlement reconciliation, karigar/job-work and advanced RBAC/audit modules remain future production modules.
