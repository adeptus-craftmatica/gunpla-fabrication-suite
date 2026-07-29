# Security Policy

Gunpla Fabrication Suite is an offline-first desktop application. It does not require an
account, does not phone home, and does not collect telemetry.

## Data handling

- All application data (collection, builds, commissions, customers, payments, photos) is stored
  locally in a per-user application data directory resolved by `platformdirs`.
- Customer and payment records never leave the local machine unless the user explicitly exports
  or backs them up.
- Secrets (future catalog-provider API keys, etc.) must never be committed to source control or
  written to log files. Use environment variables or the operating system keyring.

## Reporting a vulnerability

If you discover a security issue (e.g. a path traversal in the import/export pipeline, a way to
corrupt the local database, or unsafe handling of imported files), please open a private
security advisory on the GitHub repository, or email:

```text
adeptus.craftmatica@proton.me
```

Please do not open a public issue for suspected vulnerabilities until it has been triaged.

## Supported versions

Only the latest released version receives security fixes while the project is pre-1.0.
