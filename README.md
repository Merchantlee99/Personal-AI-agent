# Air-Gapped Agent Dashboard Scaffold

## Documentation
- [Project Overview](docs/PROJECT_OVERVIEW.md)
- [Security Model](docs/SECURITY_MODEL.md)

## Stack
- Next.js (App Router)
- Tailwind CSS + shadcn/ui style components
- SQLite (local persistence through API router)
- Docker Compose (isolated agent container)

## Quick Start
1. Copy env template:
   ```bash
   cp .env.local.example .env.local
   ```
2. Install deps:
   ```bash
   npm install
   ```
3. Run dev server:
   ```bash
   npm run dev
   ```

## Security Rules Implemented
- Client never calls external webhook directly.
- All user input must pass through `/api/proxy`.
- API route writes payloads into SQLite and can optionally forward to n8n.
- `nanoclaw-agent` runs with `read_only: true`, `cap_drop: [ALL]`, internal-only Docker network.
- Local deployment is containerized with OrbStack + Docker Compose, with routing/server/proxy boundaries separated.

## Safe Public Push Guard
Before pushing to a public GitHub repository, enable the pre-push guard:

```bash
npm run git:hooks
```

Manual check:

```bash
npm run git:guard
```

The guard blocks pushes when tracked files include runtime/sensitive paths such as:
- `.env`, `.env.local`, `.env.*.local`
- `shared_data/*`
- `.next/*`, `node_modules/*`
- `*.db`, `*.sqlite*`

It also scans tracked files for obvious API key patterns.
