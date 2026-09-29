# BIDFLUX — Design System

**AI-Powered Procurement Compliance Platform**
Target context: SIH 2026 live demonstration, desktop-first, government / enterprise.

```
AI ASSISTS. RULES VERIFY. OFFICER DECIDES. EVERYTHING IS AUDITABLE.
```

---

## 1. Principles

| # | Principle | Meaning in practice |
| --- | --- | --- |
| 1 | Professional over decorative | No gradients on data surfaces, no glassmorphism, no shadow stacks |
| 2 | Restraint in motion | Transitions limited to `150ms` colour/border only. No entrance animation on tables |
| 3 | Status is colour + icon + text | Never colour alone (accessibility + projector legibility) |
| 4 | Every number is traceable | Compliance, risk and confidence values always link back to evidence |
| 5 | Honest labelling | Mock/DEMO data is visibly marked `DEMO` / `MOCK` in the UI, never disguised |
| 6 | Density over whitespace | Compact rows; a lot fits on one screen during a live demo |

Explicitly avoided: parallax, skeleton shimmer loaders, auto-playing motion, animated charts,
colourful icon sets, emoji in data views, gradient buttons, drop shadows on text.

---

## 2. Colours

### 2.1 Core neutral ramp — "Slate" (interface chrome)

| Token | Hex | Use |
| --- | --- | --- |
| `slate-950` | `#020617` | Sidebar background, primary text headings |
| `slate-900` | `#0F172A` | Primary text |
| `slate-700` | `#334155` | Body text |
| `slate-600` | `#475569` | Secondary text, table headers |
| `slate-500` | `#64748B` | Muted text, metadata, labels |
| `slate-400` | `#94A3B8` | Placeholder, disabled icon |
| `slate-300` | `#CBD5E1` | Card/table borders |
| `slate-200` | `#E2E8F0` | Divider lines, input borders |
| `slate-100` | `#F1F5F9` | Table header background, hover row |
| `slate-50` | `#F8FAFC` | Page background, empty-state fill |
| `white` | `#FFFFFF` | Card surface |

### 2.2 Brand accent — "Gov Blue" (single accent, used sparingly)

| Token | Hex | Use |
| --- | --- | --- |
| `brand-800` | `#1E3A8A` | Primary button hover |
| `brand-700` | `#1D4ED8` | Primary button, active nav, links |
| `brand-600` | `#2563EB` | Focus ring, chart primary |
| `brand-100` | `#DBEAFE` | Selected nav background tint |
| `brand-50` | `#EFF6FF` | Info banner background |

Rule: brand colour appears on **primary actions, active navigation and links only**. It is never used
as a table background or a decorative fill.

### 2.3 Status palette

| Semantic | Text | Background | Border | Icon | Typical meaning |
| --- | --- | --- | --- | --- | --- |
| Success / PASS / VERIFIED | `#166534` | `#DCFCE7` | `#86EFAC` | ✓ CheckCircle | Requirement satisfied |
| Warning / REVIEW / HIGH | `#92400E` | `#FEF3C7` | `#FCD34D` | ⚠ AlertTriangle | Needs human judgement |
| Danger / FAIL / REJECT | `#991B1B` | `#FEE2E2` | `#FCA5A5` | ✕ XCircle | Non-compliant |
| Info / PENDING / IN PROGRESS | `#1E40AF` | `#DBEAFE` | `#93C5FD` | ● Clock / Loader | Awaiting step |
| Neutral / MISSING | `#334155` | `#F1F5F9` | `#CBD5E1` | – Minus | Not submitted / N/A |
| Mock / DEMO | `#6B21A8` | `#F3E8FF` | `#D8B4FE` | FlaskConical | Simulated, not real |

Risk levels map onto this palette:
`LOW → success`, `MEDIUM → warning`, `HIGH → danger`, `CRITICAL → danger (solid)`.

Decision badges: `APPROVED → success`, `REJECTED → danger`,
`CLARIFICATION REQUESTED → warning`, `PENDING → info`.

Confidence values `< 90%` additionally show the warning glyph.

---

## 3. Typography

**Font family:** system UI stack — no webfont download (demo must load instantly and offline).

```css
font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
             "Helvetica Neue", Arial, sans-serif;
/* numbers + IDs */
font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
```

| Role | Size / Line height | Weight | Letter spacing | Class |
| --- | --- | --- | --- | --- |
| Page title | 22 / 28 | 600 | `-0.01em` | `text-[22px] font-semibold` |
| Section title | 15 / 22 | 600 | `0` | `text-[15px] font-semibold` |
| Card title | 14 / 20 | 600 | `0` | `text-sm font-semibold` |
| Body | 13 / 20 | 400 | `0` | `text-[13px]` |
| Table body | 13 / 20 | 400 | `0` | `text-[13px]` |
| Table header | 11 / 16 | 600 | `0.04em`, uppercase | `text-[11px] uppercase tracking-wide` |
| Label / meta | 11 / 16 | 500 | `0.02em` | `text-[11px] font-medium` |
| Numeric / KPI | 26 / 30 | 700 | `-0.02em` | `text-[26px] font-bold` |
| Mono (IDs, codes) | 12 / 18 | 500 | `0` | `font-mono text-xs` |

Rules: base body size 13px; max reading width `72ch`; numerals in tables use
`tabular-nums`; all-caps reserved for table headers, badges and eyebrow labels.

---

## 4. Layout

### 4.1 App shell

```
┌──────────┬──────────────────────────────────────────────────┐
│          │  Header: page title · verification ID · env tag │
│ Sidebar  ├──────────────────────────────────────────────────┤
│ 240px    │                                                  │
│ fixed    │  Page content (max-w-7xl, px-6, py-6)           │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

- Sidebar: `w-60` (240px), fixed, full height, `bg-slate-950`, scrollable.
- Main: `ml-60`, `min-h-screen`, `bg-slate-50`.
- Header: `h-14` (56px), `bg-white`, `border-b border-slate-200`, sticky top, `z-30`.
- Content container: `max-w-7xl mx-auto px-6 py-6`, `space-y-6` between blocks.
- Content order on every workflow page:
  `Page title → Workflow stepper → Stage-specific content`.

### 4.2 Grid & spacing

- 4px base scale: `4 8 12 16 20 24 32`.
- Grid: `grid-cols-1 md:grid-cols-2 xl:grid-cols-4` for KPI cards;
  `lg:grid-cols-[2fr_1fr]` for "table + side summary" layouts.
- Table rows: `py-2.5 px-4`; card padding `p-5`; table header `py-2 px-4`.

### 4.3 Page patterns

1. **Dashboard** — 4 KPI cards → active verification card → recent verifications table.
2. **Verification list** — filterable table (`status`, `risk`) + "New Verification" primary button.
3. **Workflow page** — stepper + stage panel; only the active stage is interactive.
4. **Standalone pages** (Compliance / Evidence / Audit) — read-only, driven by the selected verification ID.

---

## 5. Sidebar

- Width 240px, `bg-slate-950`, `text-slate-300`.
- **Brand block** (top, `h-14`, `px-5`): wordmark `BIDFLUX` — `text-white font-semibold tracking-tight`
  15px, with a 6px `bg-brand-600` left bar. Sub-label `Compliance Platform` 10px `text-slate-500`.
- **Nav groups** (uppercase 10px `text-slate-500` group labels, `px-5 pt-5 pb-2`):
  - *Workspace*: Dashboard, Verification, Documents, Compliance
  - *Governance*: Evidence, Audit Trail, Reports
  - *System*: Settings
- **Nav item**: `h-9 px-5` flex, `gap-3`; icon 16px `text-slate-400`;
  label 13px; `rounded-r` only (flush against brand bar).
  - default: `text-slate-300`, transparent
  - hover: `bg-slate-900 text-white`
  - active: `bg-brand-700/15 text-white` + 3px `bg-brand-600` left indicator + `font-medium`
  - icon active: `text-brand-600`… kept white for contrast, indicator carries the colour
- **Sidebar footer** (bottom, `border-t border-slate-800`, `px-5 py-3`): environment tag
  (`DEMO` purple chip / `PRODUCTION` green chip) + API URL host, 10px `text-slate-500`.
- Icons: `lucide-react`, 16px, `stroke-width 1.75`, uniform set. No emoji.

---

## 6. Dashboard

- Title: `Dashboard`, subtitle `Procurement compliance overview` (`text-[13px] text-slate-500`).
- **KPI row** (4 cards):
  `Total Verifications` · `Pending Review` · `High Risk Cases` · `Compliance Rate`
  - value 26px/700 tabular, label 11px uppercase `text-slate-500`, icon 16px in a
    `h-8 w-8 rounded-md` tinted square (`bg-brand-50 text-brand-700`, `bg-amber-50 text-amber-700`, `bg-red-50 text-red-700`, `bg-emerald-50 text-emerald-700`).
- **Active verification card**: tender ID + title (mono ID), bidder, current step, risk badge,
  compliance progress bar, `Continue →` button → `/verification/[id]`.
- **Recent verifications table**: ID, Tender, Bidder, Status, Risk, Compliance, Updated, action.
- Empty state: dashed border box, `bg-slate-50`, message + primary CTA, no illustration.

---

## 7. Cards

- Surface: `bg-white border border-slate-200 rounded-lg` — **no shadow**.
- Header: `flex items-center justify-between px-5 py-3.5 border-b border-slate-200`;
  title `text-sm font-semibold text-slate-900`; optional right-side meta/button.
- Body: `p-5` (or `p-0` when the body is a table — table supplies its own padding).
- Footer (optional): `px-5 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg`, 12px text.
- Variants: `.card--outlined` (alert/callout cards, `border-l-4` with semantic border colour).

---

## 8. Buttons

Base: `inline-flex items-center justify-center gap-2 rounded-md font-medium
transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed select-none`.
Heights: `sm = h-8 px-3 text-[13px]`, `md = h-9 px-4 text-[13px]`, `lg = h-10 px-5 text-sm`.

| Variant | Style | Use |
| --- | --- | --- |
| Primary | `bg-brand-700 text-white hover:bg-brand-800` | Load SIH Demo, New Verification, Record Decision |
| Secondary | `bg-white text-slate-700 border border-slate-300 hover:bg-slate-50` | Cancel, secondary navigation |
| Ghost | `text-slate-600 hover:bg-slate-100` | Table row actions |
| Success | `bg-emerald-700 text-white hover:bg-emerald-800` | APPROVE |
| Danger | `bg-red-700 text-white hover:bg-red-800` | REJECT |
| Warning | `bg-amber-600 text-white hover:bg-amber-700` | REQUEST CLARIFICATION |
| Link | `text-brand-700 hover:underline` | Inline navigation |

Rule: exactly **one primary button per view**. Officer decision buttons are the only
tri-colour group and always appear in the fixed order Approve → Clarification → Reject,
with Approve (success) not given automatic primary emphasis.

Focus: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600
focus-visible:ring-offset-2` — required on all interactive elements.

---

## 9. Tables

- Wrapper: `overflow-x-auto` inside a card with `p-0` body.
- Header: `bg-slate-100 text-[11px] uppercase tracking-wide text-slate-600 font-semibold`,
  `py-2 px-4 text-left`, sticky when the table is long.
- Row: `border-b border-slate-100 px-4 py-2.5 text-[13px] text-slate-700`,
  hover `bg-slate-50`, `last:border-b-0`.
- Alignment: text left, numbers/status centre or right; numbers `tabular-nums`.
- Zebra striping: **not used** — row borders are sufficient.
- Long cells truncate to `max-w-[280px]` with `truncate` + `title` attribute.
- **Compliance matrix table** (special): 7 columns
  `Requirement | Source | Extracted Value | Verification | Status | Evidence | Action`,
  `w-full`, header sticky, row border colour reflects status at 40% opacity
  (pass → `border-emerald-200`, review → `border-amber-300`, fail → `border-red-200`).
- Empty row: single full-width cell, `py-8 text-center text-slate-500`.
- Mobile: below `md` the matrix switches to stacked cards, one requirement per card.

---

## 10. Status badges

Single primitive `<StatusBadge status tone label />`.

```
height 20px · padding 0 8px · rounded-full · text-[11px] font-medium
· inline-flex items-center gap-1 · border (1px)
· icon 12px stroke-width 2.5
```

Tones: `success | warning | danger | info | neutral | mock` (exact colours in §2.3).

Labels: uppercase for state (`PASS`, `REVIEW`, `FAIL`, `VERIFIED`, `MISSING`, `PENDING`,
`HIGH`, `APPROVED`, `REJECTED`, `DEMO`). Title case for descriptive text.

Pill used for tender/workflow status; `RiskBadge` is the same component with the risk palette
plus an uppercase letter-spacing of `0.03em`.

`ConfidenceBar`: 80px track `h-1.5 rounded-full bg-slate-200`, fill in success for ≥95%,
warning 90–94%, danger <90%; label always shows the numeric percentage.

---

## 11. Workflow UI

### 11.1 Stepper

Horizontal, 9 steps:
`Tender → Requirements → Documents → Extraction → Verification → Compliance → Risk → Review → Decision`

- Container: `bg-white border border-slate-200 rounded-lg px-4 py-3`, `overflow-x-auto`.
- Item: icon circle (24px) + label (11px) + optional connector.
- Connector: 24px `h-px` line between circles, `bg-slate-200` (complete → `bg-brand-600`).
- States:
  | State | Circle | Label |
  | --- | --- | --- |
  | Completed | `bg-brand-700 text-white` ✓ | `text-slate-600` |
  | Current | `bg-white border-2 border-brand-700 text-brand-700` | `text-slate-900 font-semibold` |
  | Pending | `bg-slate-100 border border-slate-300 text-slate-400` | `text-slate-400` |
  | Blocked | `bg-amber-100 border-amber-400 text-amber-700` | `text-slate-600` |
- Current step's label sits directly under the circle; no connector animation.
- Below `md`: horizontal scroll, no reflow. Clicking a completed step navigates.

### 11.2 Stage panels

- **Stage gate** — panel header shows `Step N of 9 · <Stage name>`, a right-aligned primary action,
  and a `DEMO` chip when the underlying service is mocked.
- **Callout** — `border-l-4 border-l-brand-600 bg-brand-50 text-slate-700 rounded-r-md
  px-4 py-3 text-[13px]`, with an info icon. Used for
  *"AI-extracted requirements require officer validation before final use."*
- **Mock banner** — `border-l-4 border-l-purple-500 bg-purple-50 text-purple-900`,
  tag `MOCK` + explanation of what is simulated and what would be real in production.
- **Document upload** — dropzone `border-2 border-dashed border-slate-300 rounded-lg
  py-8 text-center hover:border-brand-400 hover:bg-slate-50` (drag + click),
  plus a native file input as the accessible fallback.
- **Officer decision** — three buttons as §8, textarea `min-h-24`, required comment field,
  `Recording decision for <verification ID> at <timestamp>` helper text.
- **Loading** — `h-1 w-32 bg-slate-200 rounded-full animate-pulse` bar; error state =
  red banner with the API message and a Retry button. No skeleton flicker loops.

### 11.3 Evidence chain

Vertical, 6 levels: `Bidder → Document → Extracted Data → Verification → Requirement → Compliance Result`.

- Each level: `rounded-md border border-slate-200 bg-white p-3` with a
  `h-6 w-6 rounded-full bg-slate-100 text-slate-500 text-[11px] font-semibold` index chip.
- Connector: 16px vertical line `border-l border-dashed border-slate-300 ml-3`.
- Level 1 (Bidder) is expanded; deeper levels expand on click (`ChevronRight → ChevronDown`).
- Terminal node `Compliance Result` renders the status badge and the evidence hash.

---

## 12. Responsive design

| Breakpoint | Sidebar | Content | Tables | Stepper |
| --- | --- | --- | --- | --- |
| `≥1280px` (xl) | 240px fixed | `max-w-7xl` | Full columns | 9 steps inline |
| `1024–1279px` (lg) | 240px fixed | Full width | Full columns | 9 steps inline |
| `768–1023px` (md) | Off-canvas drawer + `md:` hidden, hamburger in header | `px-4` | Horizontal scroll, `min-w-[720px]` | Horizontal scroll |
| `<768px` (sm) | Drawer, 240px, overlay `bg-slate-950/40`, focus-trapped | `px-3` | Card-per-row for compliance matrix | Scroll, sticky first label |

Rules: drawer opens/closes via a 16px `Menu` / `X` icon; body scroll locks while open;
touch targets ≥40px on mobile; the workflow action bar becomes `sticky bottom-0` full-width
on mobile so the officer never has to scroll to act.

---

## 13. Motion, density and accessibility budget

- Transitions: only `background-color`, `border-color`, `color` at `150ms ease-out`.
  Plus `animate-pulse` on the single loading bar and the `animate-spin` on in-flight buttons.
- Max width of main content `1280px`.
- Contrast: all text pairs in §2.3 meet WCAG AA (≥4.5:1) on their own background.
- Focus visible on every interactive element (§8 focus ring).
- Status never conveyed by colour alone — icon + text always accompany it.
- Icons decorative → `aria-hidden`; buttons and inputs have accessible names;
  tables use `<th scope="col">`; the stepper uses `aria-current="step"`.
