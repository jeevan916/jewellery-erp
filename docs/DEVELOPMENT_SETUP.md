# Development Setup

## Target stack

- Frontend: React + TypeScript + Vite
- Backend: Django + Django REST Framework
- Database: MySQL / InnoDB
- API: REST/JSON
- Production target: Hostinger later

## Local architecture

```text
Browser
  |
  v
React + Vite
  |
  | HTTP/JSON
  v
Django + DRF
  |
  v
MySQL / InnoDB
```

## Environment configuration

Database credentials must be supplied through environment variables.

Example names only:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
DATABASE_HOST
DATABASE_PORT
```

Do not commit real credentials, API keys, tokens or passwords.

## Development database

Create a dedicated MySQL database and user for development. Use InnoDB tables and run all schema changes through Django migrations.

The application should not assume that the development database is the same server as production.

## First implementation order

1. Django project/bootstrap configuration
2. MySQL connection and migration infrastructure
3. Organizations/branches/users/RBAC primitives
4. Chart of Accounts
5. Voucher types and numbering
6. Journal entries and journal lines
7. Accounting posting service
8. Bill-wise references and allocations
9. Accounting integrity tests
10. API endpoints
11. React shell and authenticated application layout

## Quality gate

Before moving from accounting primitives to billing/inventory, tests must cover at minimum:

- balanced journal posting
- rejection of unbalanced journals
- atomic rollback
- duplicate/idempotent requests
- closed financial period protection
- bill-wise partial payment
- multi-invoice payment allocation
- customer advance/overpayment
- reversal without destructive history
- branch/tenant isolation
- unauthorized financial operation rejection

## Deployment independence

Nothing in the application code should require Hostinger-specific APIs. Hostinger is a deployment target, not a business-logic dependency.
