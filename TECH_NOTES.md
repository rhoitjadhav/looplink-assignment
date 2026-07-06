# Technical Notes

Six design decisions behind the implementation, what was cut, how to exercise
the interesting flows, AI usage, and what I'd do next.

---

## Design decisions

### 1. Validation — server is authoritative

Pydantic discriminated unions validate offer shapes on every write; lifecycle
checks enforce transition legality. The client repeats only cheap UX checks (
name non-empty, end-after-start) so the form feels responsive, but every server
409/422 is surfaced inline — the field error or banner text comes verbatim from
the server. If client and server ever drift, the user sees an explicit error
message rather than a silently accepted bad write.

### 2. Lifecycle in code — one source of truth

`lifecycle.py` holds a declarative transition table: each action maps to the
statuses it's legal from, the status it moves to, and whether it requires the
campaign to be launch-valid. `allowed_actions(campaign)` and
`launch_problems(campaign)` are called server-side and returned on every admin
response. The UI renders action buttons purely from
`campaign.allowed_actions` — it never computes legality itself. Client and
server cannot drift because the client's rendering input is the server's
enforcement output.

### 3. Stale state — optimistic locking via `version`

Every PUT and POST to `/transitions` must include the `version` the client last
read. If the DB row has moved on (another tab, another user), the check fails
with `409 version_conflict`. The form and detail page catch that code
explicitly and prompt a reload with a clear message. A draft that was launched
while the form was open trips a separate `409 status_conflict` (draft-only edit
rule) — either way the write is rejected with a human reason, never silently
merged or lost.

### 4. Link / QR encoding

The QR link encodes only a random `public_token` (12 characters). We are not
using DB UUID, status or expiry.
Links are permanent identifiers, the campaign's status controls access.
The public endpoint collapses `draft` and `scheduled` into a single `not_open`
state (shoppers never see internal lifecycle detail), returns `ended`.

### 5. Identity without auth

Identity is accepted as email or phone, type-detected by presence of `@`. Email
is trimmed and lowercased; phone is stripped to digits with an optional leading
`+`, with a 7–15 digit length sanity check. Dedup is enforced by a DB unique
constraint on `(campaign_id, identity_normalized)` with
`ON CONFLICT DO NOTHING` on insert. The returning clause tells us whether the
row was inserted or conflicted, so `already_enrolled: true/false` is reliable
and a concurrent double-submit cannot create two rows.

### 6. One model, two audiences

One `Campaign` row, two Pydantic response schemas: `CampaignAdmin` (id,
version, status, token, allowed_actions, enrollment_count, etc.) and
`CampaignPublic` (name, description, offers only). Each admin/public router
serializes these schemas respectively.
---

## What I cut (and why)

- **Auth / multi-tenancy** — explicitly out of spec.
- **Auto-transitions (scheduler)** — out of spec and removed. Status changes
  are manual-only; a live campaign whose window has passed stays live until
  explicitly ended.
- **Coupon / code generation** — out of spec.
- **E.164 phone validation** — out of spec; length-sanity only.
- **SKU catalog validation** — out of spec; free-text `applies_to`.
- **Timezone rendering** — all datetimes are UTC throughout; no TZ conversion.
- **Pagination / filtering** — not needed at demo scale.
- **Styling framework** — single `index.css`; not worth the setup time.
- **Editing non-draft campaigns** — per spec; the server enforces it, the UI
  reflects it.

---

## How to exercise the interesting flows

- **Blocked action** — create a campaign with no offers and no window. The "
  Schedule" and "Launch now" buttons will be absent; the "Attach at least one
  offer" and window hints appear instead. To confirm server enforcement too:
  `curl -X POST .../transitions -d '{"action":"launch","version":1}'` → 409
  `illegal_transition`.
- **Non-live scan** — open `/c/<token>` for a draft campaign → "isn't open
  yet". End a live campaign and refresh the same link → "has ended".
- **Stale edit** — open the edit form for a draft in two browser tabs. Save in
  tab A. Save in tab B → 409 `version_conflict` banner with a Reload button.
- **Repeat enrollment** — enroll with `" Rohit@Example.COM "`, then enroll
  again with `"rohit@example.com"` → "Welcome back — you're already enrolled."
- **Launched-while-editing** — open the edit form for a draft in one tab,
  launch it from the detail page in another, then save the form → 409
  `status_conflict` with a link back to the detail page.

---

## AI usage

My background is backend-heavy, so I used Claude to generate all frontend
code (React components, routing, API client, CSS). I drove it with explicit
requirements — schema shapes, error codes, UX states — reviewed every file it
produced, and adjusted where output diverged from intent (e.g. version-conflict
state wiring, offer field coercion before submit). I own the decisions; the AI
accelerated the React surface I'd otherwise have spent more time on.

Backend code (FastAPI routers, lifecycle engine, Pydantic schemas, Alembic
migration, identity normalisation) was written by hand. I used Claude as a
sounding board for a few edge cases (concurrent enroll dedup, optimistic lock
pattern) but the code is mine.

---

## Known limitations

- Phone validation is length-sanity only (7–15 digits), not E.164
- Auto-transitions run every 5s in-process — dies if the server restarts
  mid-window
- No soft delete / archive, the ended campaigns accumulate forever
- No pagination on campaign list
- `applies_to` on offers is free text, no catalog validation or enforcement
- No rate limiting on the public enroll endpoint
- Migrations must be run manually — no CI enforcement
- All datetimes shown as UTC with no conversion

## Future Improvements

- For `update_campaign`, add **row locking** on campaign as it will fix race
  condition.
- Add **Authentication & Authorization** on protected routes.
- OTP verification on enrollment.
- Isolate APScheduler for auto-transitions
- **Pagination** & **filtering** on campaign list
- CI/CD Pipeline for DB migration, and deployment
- Add Observability for monitoring & alerting
- Include sharable mediums for campaign QR codes and link using Email, SMS,
  etc. to shoppers
