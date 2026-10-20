# Green Vita — Token Migration Map

Version: 1.0
Status: Audit complete / Migration not started

هدف:
تبدیل چند سیستم token قدیمی به یک Green Vita Design Token Layer واحد.

---

## 01 — Canonical Tokens

Canonical source:

src/admin/static/css/gv-tokens.css

این فایل مرجع نهایی توکن‌هاست.

---

## 02 — Core Legacy Mapping

| Legacy token | Canonical token |
|---|---|
| --gv-primary | --gv-color-primary |
| --gv-primary-dark | --gv-color-primary-dark |
| --gv-bg | --gv-color-bg |
| --gv-surface | --gv-color-surface |
| --gv-surface-soft | --gv-color-surface-soft |
| --gv-text | --gv-color-text |
| --gv-text-soft | --gv-color-text-soft |
| --gv-muted | --gv-color-text-muted |
| --gv-border | --gv-color-border |
| --gv-gold | --gv-color-gold |
| --gv-gold-soft | --gv-color-gold-soft |
| --gv-success | --gv-color-success |
| --gv-warning | --gv-color-warning |
| --gv-danger | --gv-color-danger |
| --gv-radius-sm | --gv-token-radius-sm |
| --gv-radius-md | --gv-token-radius-md |
| --gv-radius-lg | --gv-token-radius-lg |
| --gv-radius-xl | --gv-token-radius-xl |
| --gv-shadow-sm | --gv-token-shadow-sm |
| --gv-shadow | --gv-token-shadow-md |
| --gv-shadow-hover | --gv-token-shadow-lg |

---

## 03 — admin.css Legacy Mapping

| Legacy token | Canonical token |
|---|---|
| --green | --gv-color-primary |
| --green-dark | --gv-color-primary-dark |
| --green-light | --gv-color-primary-soft |
| --cream | --gv-color-bg |
| --cream-soft | --gv-color-surface-soft |
| --ink | --gv-color-text |
| --muted | --gv-color-text-muted |
| --white | --gv-color-surface |
| --danger | --gv-color-danger |

---

## 04 — gv-modern-admin.css Mapping

| Legacy token | Canonical token |
|---|---|
| --gv-primary | --gv-color-primary |
| --gv-primary-dark | --gv-color-primary-dark |
| --gv-primary-soft | --gv-color-primary-soft |
| --gv-cream | --gv-color-bg |
| --gv-white | --gv-color-surface |
| --gv-text | --gv-color-text |
| --gv-muted | --gv-color-text-muted |
| --gv-border | --gv-color-border |

---

## 05 — smart-bio.css Mapping

The old Smart Bio palette must migrate to the canonical system.

Primary:
#8BC53D

Primary Dark:
#022F12

Soft:
#E4F0CC

Gold:
#C6A15B

Gold Soft:
#E8D8B5

Text:
#021408

Muted:
#7C8B82

---

## 06 — green-vita-ui.css

The following are NOT automatically replaced:

--gv-green-950
--gv-green-900
--gv-green-800
--gv-green-700
--gv-green-600

Reason:
They form a local green scale used by existing public/booking components.

Migration requires component-level review before replacement.

The same applies to:

--gv-cream
--gv-cream-2
--gv-paper
--gv-paper-dark
--gv-brown
--gv-rust
--gv-gold-light

These must be mapped by visual role, not by blind name replacement.

---

## 07 — Hard-coded Legacy Colors

Legacy colors detected:

#4F7F4F
#355D3B
#2F6B3F
#234F2F
#3F7449
#285333
#0B493F
#0F5B4F
#146B5D
#1C806D
#B99A5C
#D5BD86

They are migration candidates.

DO NOT replace them globally until:
1. selector is inspected
2. component role is identified
3. canonical token is chosen
4. visual regression is checked

---

## 08 — Migration Order

Phase 1:
Canonical tokens ✅

Phase 2:
Token mapping document ✅

Phase 3:
Update legacy :root definitions to reference canonical tokens

Phase 4:
Connect gv-tokens.css

Phase 5:
Migrate component styles

Phase 6:
Migrate page-specific styles

Phase 7:
Remove duplicate token definitions

Phase 8:
Remove obsolete theme layers

---

## 09 — Important Rule

Never solve CSS conflicts by adding:

- final-v2.css
- redesign-v2.css
- theme-new.css
- override-final.css
- another !important layer

The solution must be architectural:

tokens
→ primitives
→ components
→ pages

---

## 10 — Current Legacy Files

admin.css
dashboard-redesign.css
global-vazir.css
gv-luxury-theme.css
gv-modern-admin.css
green-vita-ui.css
green-vita-final.css
booking-prototype.css
public-shared-header.css
smart-bio.css

---

## 11 — Migration Safety

Before each migration batch:

1. create backup
2. make smallest logical change
3. inspect git diff
4. validate syntax
5. restart/reload only if required
6. perform visual review
7. commit only after verification

---

Status:
READY FOR TOKEN REFACTOR
