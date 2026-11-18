# Architecture and Security

This document describes how the reference demo is built, what it deliberately does not
do, and what would have to change before anything like it held real asset records.

## Scope

AssetFlow is a demonstration of an architecture, not a product. The organisation and the
portfolio are invented, nothing is read from or written to another system, and the state
lives in memory. It is not a system of record.

## Components

| Component | Responsibility |
| --- | --- |
| React single-page app | Renders one portfolio snapshot at a time; sends commands |
| Nginx | Serves the static bundle and proxies `/api/` to the backend |
| FastAPI routers | Read side (`/state`, `/stream`), asset commands, trash commands, import and export |
| `PortfolioEngine` | Owns all mutable state; validates, mutates, audits, purges and publishes |
| `pipelines.py` | The four pipelines and their ordered stages |
| `intake.py` | The one model that validates a new asset, from the API or from a CSV row |
| `views.py`, `analytics.py` | Read side: asset views with retention, boards, KPIs |
| Broadcaster | Fans snapshots out to every connected stream client |
| `exchange/` | CSV import and export, workbook export, formula neutralisation |

## Data flow

1. At startup the sixteen seed assets are built through the same validation model as an
   imported row. Two of them are given a deletion time in the past, so the trash bin is
   not empty.
2. A command such as `PATCH /assets/AST-401/stage` reaches the engine, which first reads
   the clock (and purges anything whose retention has ended), then checks the asset
   exists, is not in the trash bin, and that the target is a stage of its own pipeline.
3. If every check passes the engine changes the state, writes the audit entry and
   publishes one snapshot. If any check fails it raises a refusal and changes nothing:
   no audit entry, no snapshot.
4. Each stream client has its own bounded queue. The stream sends a `snapshot` event on
   connect, `update` events afterwards, and a `heartbeat` event when nothing was
   published for five seconds.

### Deletion has one source of truth

An asset carries `deleted_at`: a UTC time, or null while it is active. Nothing else is
stored. `is_deleted`, `retention_days_left` and `purge_at` are computed for each response
from `deleted_at`, the retention period and the clock, so they cannot disagree with it.

`retention_days_left` is rounded up: an asset with two hours left shows one day, never
zero. When the retention period has fully elapsed the asset is purged. There is no
background job; the purge happens whenever the engine reads the clock, which every state
read and every command does. An expired asset is therefore never shown and never
restored, even if no client was connected when its time ran out. The clock is injected,
and the tests move it to check each of these statements.

Restoring only clears `deleted_at`. The pipeline and stage were never changed by the
delete, so the asset returns exactly where it was.

### KPIs

Every figure is computed in the backend from active assets only, and the workbook export
is built from the same snapshot, so the screen and the file agree. Money is a `Decimal`
from validation to JSON, where it travels as a string; the frontend formats it and never
adds amounts up.

### Why full snapshots instead of deltas

Every event carries the complete state. That costs some kilobytes per message and buys
three properties: a client is consistent after one message, a dropped message cannot
leave a client with a wrong picture, and a slow client can simply skip to the newest
snapshot. The cost grows with the portfolio, which is one reason an import is capped at
500 rows.

### Why Server-Sent Events

The data flows one way, from server to screen. SSE runs over plain HTTP, passes through
proxies without special handling, and browsers reconnect on their own. Commands go
through ordinary requests, so nothing needs a bidirectional channel.

### Why a single worker

State lives in the process. Two workers would hold two different portfolios and clients
would see either one at random. Scaling out would require moving state and fan-out to a
shared store, which this demo intentionally leaves out.

### Connection health

A proxy can keep the browser side of a stream open after the backend has died. The
browser does not report that case. The client therefore treats eight seconds without any
event as a dead connection, shows `RECONNECTING` and then `DISCONNECTED`, and keeps
retrying until the stream returns. Once disconnected, the controls are disabled: a
command sent from a stale screen could act on a stage that has already changed.

## CSV import

The body is read with a hard limit of 256 KB, enforced while reading and not only from
the declared length. It must be UTF-8; a byte-order mark is accepted. The import then
proceeds in two steps.

1. **The header decides whether the file is read at all.** A missing, unknown or repeated
   column rejects the file with a message that names the columns and lists the expected
   ones. So does an empty file, a file over 500 data rows, or malformed CSV.
2. **Rows are judged one by one.** A valid row is imported. An invalid row is reported
   with its line number, the column, the value and the reason, and the rest of the file
   still goes in. The checks are the same model `POST /assets` uses: enumerations,
   whether the stage belongs to the pipeline, numeric ranges, latitude and longitude
   ranges, two decimal places for money, and a fixed list of boolean spellings.

An `asset_id` that is repeated inside the file, already active or present in the trash
bin is a row error. Nothing is ever overwritten, and a deleted asset cannot be
resurrected or replaced by an import. A blank id is assigned by the server after the
rows that bring their own, so an assigned id never collides with one in the file.

If no row is imported, nothing is published.

### Formula injection

A name such as `=HYPERLINK(...)` is harmless in the browser, where React escapes it, but
a spreadsheet would run it. Every text cell written to the sample CSV or to the workbook
is therefore prefixed with an apostrophe when it starts with `=`, `+`, `-`, `@`, a tab or
a carriage return, and workbook text is stored as a literal string. Numbers are written
as numbers and are not altered, so a negative longitude stays a number.

## On-premises posture

The stack is designed to run with no outbound network access:

- no CDN assets, no web fonts, no analytics, no third-party API calls;
- the interactive API documentation page is disabled because it would load assets from a
  public CDN (the OpenAPI schema is still served locally);
- the two containers talk over the internal Compose network and only the frontend port
  is published;
- charts are drawn as SVG with attributes, not inline styles, so they render under a
  Content Security Policy without `unsafe-inline`;
- CI fails if the built bundle names a host other than the licence and XML namespace
  strings that React and Tailwind ship.

Building the images does need a registry and package indexes. An air-gapped site would
build elsewhere and import the images, or use internal mirrors.

## Security controls in this repository

| Control | Where |
| --- | --- |
| Port bound to `127.0.0.1` only | `docker-compose.yml` |
| Backend not published to the host | `docker-compose.yml` |
| Containers run as non-root, read-only root filesystem (size-capped in-memory `/tmp` only), all capabilities dropped, `no-new-privileges` | `docker-compose.yml`, Dockerfiles |
| Health check defined once | `backend/Dockerfile` |
| Content Security Policy (same origin only), `X-Frame-Options`, `nosniff`, `Referrer-Policy` | `frontend/nginx.conf` |
| Same-origin API through the proxy, so no CORS is enabled | `frontend/nginx.conf`, `vite.config.ts` |
| Asset ids validated by pattern; unknown body fields refused | `backend/app/intake.py`, `backend/app/api/` |
| Every rule enforced in the backend, never only in the UI | `backend/app/engine.py` |
| Import size and row limits; no overwrite | `backend/app/exchange/csv_import.py` |
| Formula neutralisation in CSV and workbook output | `backend/app/exchange/safe_text.py` |
| Exact dependency versions, lockfile for the frontend, monthly update proposals | `requirements.txt`, `package-lock.json`, `.github/dependabot.yml` |
| Bounded per-client queues | `backend/app/broadcaster.py` |

## Known gaps

These are accepted for a demo and would be blockers anywhere else.

- **No authentication or authorisation.** Anyone who can reach the port can move, delete,
  purge and import. This is why the port is bound to localhost.
- **The audit trail says what and when, not who.** There are no users, so there is no
  actor to record. It is also in memory, and a purge removes it with the asset.
- **Purge is immediate and final.** There is no second approval and no export before
  removal.
- **No TLS.** Traffic is plain HTTP.
- **No rate limiting and no cap on stream connections.** A client can open many streams,
  and repeated imports can grow the portfolio without bound.
- **No persistence.** All state is lost on restart.
- **No concurrency control.** Two clients can act on the same asset one after the other;
  the second sees the first one's result but is not warned.
- **Expiry is not announced.** An asset purged for retention disappears at the next
  snapshot; no event is published at the exact moment it expires.

## What a real deployment would add

- **Authentication and roles**, backed by the organisation's directory: who may move an
  asset in each pipeline, who may delete, who may restore and who may purge. The audit
  trail would then record the authenticated user.
- **Persistence** in a database, with `deleted_at` as a column, the audit trail in an
  append-only table that outlives a purge, and backups.
- **A scheduled retention job**, with a notice before an asset is purged and a legal-hold
  flag that suspends the clock.
- **Ordered workflows**: allowed transitions per pipeline, required documents per stage
  checked against stored files, and approvals for the stages that commit capital.
- **Import as a reviewed change**: a preview of what a file would add, an explicit
  update mode with a diff, and the file kept as evidence.
- **Optimistic concurrency**: each command carries the version it was based on and is
  refused if the asset changed since.
- **Real location data handled with care**: precise coordinates of critical
  infrastructure are sensitive and would need their own access rules.
- **TLS** terminated at the proxy with certificates from the organisation's authority.
