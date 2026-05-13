# Hospitality Talent Cloud

A bold, multi-tenant recruitment portal for hotel groups.
One pipeline for every property.

## What's in this repository

| File | Purpose |
|------|---------|
| `SPECIFICATION.md` | The product specification, written in plain language so a business user can edit it directly. Every requirement is numbered (REQ-XXX) for traceability. |
| `index.html` | A fully-interactive look-and-feel prototype of the portal — multi-tenant switcher, dashboard with live KPIs, kanban pipeline with drag-and-drop, candidate explorer with filters, job board, and CSV import flow. |
| `vercel.json` | Static-site deployment configuration for [Vercel](https://vercel.com). |

The prototype is a single static `index.html` — no build step, no
dependencies. Open it locally or host it anywhere that serves static files.

## Run it locally

Any of the following will work:

```bash
# 1. Just open the file
open index.html

# 2. Or serve it from the directory
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Deploy to Vercel

### Option A — connect the GitHub repo (recommended)

1. Sign in at [vercel.com](https://vercel.com) and click **Add New… → Project**.
2. Import this GitHub repository.
3. Framework preset: **Other**. Root directory: `./`. Build command: *(none)*.
   Output directory: `./`.
4. Click **Deploy**. The `vercel.json` in the repo applies sensible security
   headers and clean URLs.

Every push to the `claude/recruitment-portal-dashboard-JbuV5` branch will create
a preview URL; merging to `master` will publish to production.

### Option B — one-shot CLI deploy

```bash
npx vercel        # preview deploy
npx vercel --prod # production deploy
```

You will be prompted to authenticate the first time.

## Demoing the prototype

- The **tenant switcher** in the top bar reskins the portal for *Aurora
  Hotels*, *Meridian Resorts*, or *Sable Collection*.
- The **kanban board** under *Pipeline* supports drag-and-drop between
  stages — every move pops a toast and updates the column counts.
- The **candidates view** supports filter chips and free-text search
  (try `⌘K` / `Ctrl+K` to focus the search bar).
- The **import view** previews the drag-and-drop CSV / CV upload flow.

## Editing the specification

Open `SPECIFICATION.md` in any markdown editor (VS Code, Obsidian, GitHub's
web editor). Each requirement is identified as `REQ-XXX` — reference these
numbers in tickets, comments, and review meetings. To strike a requirement,
wrap it in `~~ ~~`. Add new ones at the end of the relevant section.

Section 18 of the spec lists the open questions that need a business owner's
answer before development begins.
