# Technical Notes

Six design decisions behind the implementation, what was cut, how to exercise the interesting flows, AI usage, and what I'd do next.

---

## Design decisions

### 1. Validation — server is authoritative

Pydantic discriminated unions validate offer shapes on every write; lifecycle checks enforce transition legality. The client repeats only cheap UX checks (name non-empty, end-after-start) so the form feels responsive, but every server 409/422 is surfaced inline — the field error or banner text comes verbatim from the server. If client and server ever drift, the user sees an explicit error message rather than a silently accepted bad write.

### 2. Lifecycle in code — one source of truth

`lifecycle.py` holds a declarative transition table: each action maps to the statuses it's legal from, the status it moves to, and whether it requires the campaign to be launch-valid. `allowed_actions(campaign)` and `launch_problems(campaign)` are called server-side and returned on every admin response. The UI renders action buttons purely from `campaign.allowed_actions` — it never computes legality itself. Client and server cannot drift because the client's rendering input is the server's enforcement output.

### 3. Stale state — optimistic locking via `version`

Every PUT and POST to `/transitions` must include the `version` the client last read. If the DB row has moved on (another tab, another user), the check fails with `409 version_conflict`. The form and detail page catch that code explicitly and prompt a reload with a clear message. A draft that was launched while the form was open trips a separate `409 status_conflict` (draft-only edit rule) — either way the write is rejected with a human reason, never silently merged or lost.

### 4. Link / QR encoding

The QR link encodes only a random `public_token` (12 characters, URL-safe base64, ~72 bits of entropy) — never the DB UUID, never status, never expiry. Links are permanent identifiers; the campaign's status controls access. The public endpoint collapses `draft` and `scheduled` into a single `not_open` state (shoppers never see internal lifecycle detail), returns `ended` distinctly so the page can say so, and the `CampaignPublic` schema physically cannot include fields that aren't in it — leaking internals is a type error, not a code-review catch.

### 5. Identity without auth

Identity is accepted as email or phone, type-detected by presence of `@`. Email is trimmed and lowercased; phone is stripped to digits with an optional leading `+`, with a 7–15 digit length sanity check (not E.164 — deliberately, per spec). Dedup is enforced by a DB unique constraint on `(campaign_id, identity_normalized)` with `ON CONFLICT DO NOTHING` on insert. The returning clause tells us whether the row was inserted or conflicted, so `already_enrolled: true/false` is reliable and a concurrent double-submit cannot create two rows.

### 6. One model, two audiences

One `Campaign` row, two Pydantic response schemas: `CampaignAdmin` (id, version, status, token, allowed_actions, enrollment_count, …) and `CampaignPublic` (name, description, offers only). The public router serializes only `CampaignPublic`, so the internal-vs-shopper boundary is enforced at the serialization layer in `schemas.py`. Offers use JSONB validated by the discriminated union — three heterogeneous shapes in one column, pragmatic for a single team moving fast.

---

## What I cut (and why)

- **Automated tests** — timebox. The companion `looplink-tests-plan.md` contains a full pytest suite; restore it before submission if time allows.
- **Auth / multi-tenancy** — explicitly out of spec.
- **Auto-transitions (scheduler)** — out of spec; status changes are manual-only.
- **Coupon / code generation** — out of spec.
- **E.164 phone validation** — out of spec; length-sanity only.
- **SKU catalog validation** — out of spec; free-text `applies_to`.
- **Timezone rendering** — all datetimes are UTC throughout; no TZ conversion.
- **Pagination / filtering** — not needed at demo scale.
- **Styling framework** — single `index.css`; not worth the setup time.
- **Editing non-draft campaigns** — per spec; the server enforces it, the UI reflects it.

---

## How to exercise the interesting flows

- **Blocked action** — create a campaign with no offers and no window. The "Schedule" and "Launch now" buttons will be absent; the "Attach at least one offer" and window hints appear instead. To confirm server enforcement too: `curl -X POST .../transitions -d '{"action":"launch","version":1}'` → 409 `illegal_transition`.
- **Non-live scan** — open `/c/<token>` for a draft campaign → "isn't open yet". End a live campaign and refresh the same link → "has ended".
- **Stale edit** — open the edit form for a draft in two browser tabs. Save in tab A. Save in tab B → 409 `version_conflict` banner with a Reload button.
- **Repeat enrollment** — enroll with `" Rohit@Example.COM "`, then enroll again with `"rohit@example.com"` → "Welcome back — you're already enrolled."
- **Launched-while-editing** — open the edit form for a draft in one tab, launch it from the detail page in another, then save the form → 409 `status_conflict` with a link back to the detail page.

---

## AI usage

I planned the architecture and drafted the implementation using Claude. I reviewed every generated file, ran each verification step (curl, Playwright), and adjusted code where the output differed from intent — e.g. fixing the Alembic enum downgrade, wiring the React state correctly for version-conflict detection. I can walk through any part of the codebase and explain the decisions.

---

## Next steps

- Real-time enrollment count on the detail page (SSE or polling).
- Soft-delete / archive for ended campaigns.
- Rate-limiting on the public enroll endpoint (per token, per IP).
- Run migrations in CI against a throwaway Postgres container.
- Accessibility audit of the public page (contrast, focus management).
