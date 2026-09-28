# PostgreSQL recovery drill record

This record documents the Phase 2.8.1 integration drill performed on 2026-09-28. It is evidence for the repository baseline, not a substitute for repeating recovery against each deployment's own backup and infrastructure.

## Isolation

- Source: dedicated `postgres:16-alpine` container with a newly migrated `timberops_source` database
- Target: a second dedicated `postgres:16-alpine` container
- Restore destination: newly created `timberops_restored` database
- Existing TimberOps Compose services, databases, and volumes were not connected, overwritten, or removed

The source contained one drill-only user, vehicle, customer, completed weighing task, billing record, and audit log, plus two weighing records.

## Procedure

1. Upgraded an empty PostgreSQL 16 source database through every Alembic revision.
2. Confirmed `alembic check` reported no pending upgrade operations.
3. Seeded a connected business-data chain using the existing ORM models.
4. Ran `python scripts/backup_db.py --container <source>`.
5. Produced a PostgreSQL custom-format archive and SHA-256 manifest.
6. Ran `python scripts/restore_db.py <archive> --container <target> --target-database timberops_restored --confirm-restore`.
7. Queried the restored database to verify revisions, core tables, row counts, and relationships.
8. Repeated the restore against the same target name and confirmed it was refused without changing restored data.

## Results

- Archive size: 37,257 bytes
- Restored Alembic revision: `d8a3f6c1b954`
- Required table counts: `users=1`, `vehicles=1`, `customers=1`, `weighing_tasks=1`, `weighing_records=2`, `billing_records=1`, `audit_logs=1`
- Relationship verification joined the completed task to its vehicle, customer, two readings, billing record, audit event, and operator
- Existing-target protection returned a failure and preserved `weighing_tasks=1`
- Dedicated drill containers, anonymous volumes, and local drill archives were removed after verification

## Production reminder

Repeat this procedure using a current production backup before every release that changes the schema and at the interval defined by the deployment owner. Retain the real archive in encrypted, access-controlled off-host storage; never commit it to Git.
