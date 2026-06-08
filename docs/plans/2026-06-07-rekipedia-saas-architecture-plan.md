# Rekipedia SaaS (rekipedia-cloud) Architecture Plan

Date: 2026-06-07
Author: Eddie & Hermes Agent
Status: Proposed / Planning

---

## 1. Overview
The goal is to convert the open-source `rekipedia` codebase-to-wiki CLI into a commercial, cloud-native Software-as-a-Service (SaaS) platform named **Rekipedia Cloud** (or `rekipedia-cloud`). 

To preserve the open-source spirit and maintain modularity, the SaaS implementation will live in a **completely separate, private repository** (e.g., `rekipedia-saas` or `rekipedia-cloud`). The open-source `rekipedia` CLI will remain public under the MIT license as the foundational engine.

---

## 2. Core Architectural Philosophy
- **Separation of Concerns**: Open-source CLI handles extraction, static analysis, page generation, and local serving. The SaaS platform handles tenancy, multi-user collaboration, secure sandboxed execution, billing, and web-based interaction.
- **Database-per-Repository (Physical Isolation)**: Instead of maintaining a massive centralized vector/relational database for all source code files and semantic embeddings, we leverage the existing `.rekipedia/store.db` (SQLite) structure. S3/Cloud Storage acts as the encrypted storage vault. Each repository's knowledge state is hydrated on-demand.
- **Zero-Trust Sandboxing**: Code analysis requires cloning customer source code. Scanning must run in isolated, short-lived, ephemeral container environments to protect the SaaS host.
- **Modern Next.js Frontend**: Transition the Jinja2-based `reki serve` interface into a highly polished, responsive Single Page Application (SPA) using Next.js, Shadcn UI, and interactive visualization tools like React Flow.

---

## 3. High-Level Architecture Block Diagram

```
[ User Browser ]
       │ (HTTPS / WebSockets)
       ▼
┌────────────────────────────────────────────────────────┐
│              Next.js Web Application                   │
│   - Routing (App Router)                               │
│   - Authentication (Clerk / Auth0)                      │
│   - Subscriptions (Stripe Integration)                 │
│   - Frontend UI (Shadcn UI, Tailwind)                  │
│   - Interactive Graphs (React Flow / D3)               │
└──────┬──────────────────────────────────────────┬──────┘
       │ (Fetch / SQLite queries)                 │ (Job Queue)
       ▼                                          ▼
┌────────────────────────────────┐       ┌────────────────────────────────┐
│      SaaS Metadata DB          │       │      Message / Job Queue       │
│ - PostgreSQL (Prisma/Drizzle)  │       │ - Redis / BullMQ / Celery      │
│ - Users, Orgs, Billing, Repos  │       └────────────────┬───────────────┘
└────────────────────────────────┘                        │ (Spawn Job)
                                                          ▼
┌────────────────────────────────┐       ┌────────────────────────────────┐
│      Secure Storage Vault      │◄──────┤       Ephemeral Workers        │
│ - AWS S3 / Cloud Storage       │ (Save │ - AWS Fargate / Fly.com        │
│ - Key: {user_id}/{repo}/db     │  DB)  │ - Ephemeral docker sandboxes   │
└────────────────────────────────┘       │ - Runs `reki scan` + `embed`   │
                                         └────────────────────────────────┘
```

---

## 4. Key Components Detail

### A. Next.js Base Web Application (`/apps/web`)
The user-facing portal where users log in, manage their synced repositories, view the generated documentation wikis, view hotspot reports, and chat with their codebases.

- **Routing & Framework**: Next.js App Router (React Server Components).
- **Authentication**: Clerk or Auth0 for enterprise-ready OAuth logins (GitHub, GitLab, Bitbucket).
- **Billing**: Stripe Checkout and Stripe Webhooks (Starter / Team / Enterprise tiers).
- **Wiki Navigation**: Next.js Client-side Navigation. Renders the `.md` pages stored in the repo-specific S3 vault instantly with no page-reload flicker.
- **Hotspots & Dependency Visualization**: Integrated React components using **React Flow** to render interactive class hierarchies and module dependency graphs.
- **RAG Chat Panel**: Underpinned by **Vercel AI SDK**, offering real-time streaming answers from the RAG engine over SSE.

### B. Secure Sandboxed Workers (`/apps/worker`)
A dedicated background processing tier that handles cloning and scanning repositories.

- **Workflow**:
  1. Next.js triggers a scan job via BullMQ/Celery when a webhook is received (e.g., GitHub push event) or on manual click.
  2. Worker spins up a new isolated container (e.g., AWS Fargate, Fly.com Machine, or gVisor sandbox).
  3. Worker clones the repository using temporary OAuth tokens.
  4. Worker runs `reki scan .` and `reki embed .`.
  5. Worker extracts the generated `.rekipedia/store.db` and the `.rekipedia/wiki/` directory.
  6. Worker compresses these artifacts and uploads them to the secure Storage Vault (S3).
  7. Worker container is immediately destroyed.

### C. S3 SQLite Storage Strategy (On-Demand Hydration)
To avoid the astronomical costs and complex multi-tenant query performance issues of a massive centralized vector database, we use S3 as a cold/warm vault.

- **How querying works (Wiki & Ask)**:
  - When a user asks a question or views a wiki page on the Next.js dashboard, the Next.js API route downloads the specific repo’s `store.db` file from S3 to local temporary storage (`/tmp/` disk or an in-memory SQLite buffer).
  - The API route queries the local database file using `better-sqlite3` (for Node.js) or a lightweight Python microservice.
  - Since `better-sqlite3` is incredibly fast (executing queries in microseconds), the download and query overhead is negligible (especially when cached in local container memory for active users).
  - This guarantees **absolute tenant separation and isolation** at the database level.

---

## 5. Transition Path from local `reki serve` to Next.js
1. **API Migration**:
   - Extract the core query logic from `rekipedia/src/rekipedia/server/app.py` into distinct API endpoints.
   - For Node.js-based Next.js, port the SQL queries directly from Python into raw SQLite queries using `better-sqlite3`.
2. **Markdown Rendering**:
   - Instead of Jinja2 rendering, use `next-mdx-remote` or simple Markdown parser packages inside Next.js Server Components.
3. **SSE to Vercel AI SDK**:
   - Replace the custom Starlette `StreamingResponse` with Vercel AI SDK's streaming wrappers for clean, reliable streaming to UI React hooks.

---

## 6. Action Items for Future Implementation
- [ ] Create a new private repository: `rekipedia-cloud`.
- [ ] Scaffold a standard monorepo (e.g., using Turborepo) with Next.js and the background worker structure.
- [ ] Implement the S3 storage sync logic in the open-source CLI (as an optional export command: `reki export --format db`) or run it directly in the cloud worker.
- [ ] Design the Next.js landing page and dashboard Mockups.
