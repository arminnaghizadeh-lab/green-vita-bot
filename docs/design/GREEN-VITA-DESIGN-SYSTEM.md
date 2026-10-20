# Green Vita — Design System v1.0

Status: Approved foundation
Scope: Admin + Public + Booking
Direction: Luxury / Natural / Medical / Modern
Language: Persian (RTL)
Accessibility: WCAG-aware
UI reference: UI/UX Pro Max + 21st.dev principles

---

## 01 — Brand Direction

Green Vita should feel:

- Professional
- Trustworthy
- Natural
- Medical
- Calm
- Premium
- Modern

Avoid:

- Generic hospital UI
- Generic SaaS dashboard appearance
- Excessive gradients
- Excessive glassmorphism
- Bright/shiny yellow gold
- Decorative UI that reduces usability
- Too many cards
- Multiple competing visual systems

---

## 02 — Core Color Tokens

### Brand

--gv-color-primary: #8BC53D
--gv-color-primary-dark: #022F12
--gv-color-sidebar: #021408
--gv-color-primary-soft: #E4F0CC

### Surfaces

--gv-color-bg: #F7FAF2
--gv-color-surface: #FFFFFF
--gv-color-surface-soft: #F5F8EF
--gv-color-highlight: #E4F0CC

### Text

--gv-color-text: #021408
--gv-color-text-soft: #496054
--gv-color-text-muted: #7C8B82

### Border

--gv-color-border: #DCE6D7
--gv-color-border-soft: #EAF0E6

### Premium Accent

--gv-color-gold: #C6A15B
--gv-color-gold-soft: #E8D8B5

Gold is an accent only.
Never use gold as the main CTA color.

### Semantic Status

--gv-color-success: #3E7D4A
--gv-color-warning: #B98523
--gv-color-danger: #C94A4A
--gv-color-info: #3D708F

Status meaning must not depend on color alone.

---

## 03 — Typography

Primary Persian font:

"Vazirmatn"

Fallback:

Tahoma, "Segoe UI", Arial, sans-serif

Do not use multiple competing Persian font families.

Recommended hierarchy:

Display:
40–48px / 700

H1:
32–40px / 700

H2:
26–32px / 700

H3:
21–24px / 700

Body:
15–16px / 400–500

Small:
13–14px / 400–500

Caption:
12–13px / 400

Line height:

Body: 1.75–1.9
Heading: 1.35–1.5

---

## 04 — Spacing Scale

Use a predictable spacing system:

4
8
12
16
20
24
32
40
48
64
80

Avoid arbitrary spacing values unless required by a component.

---

## 05 — Radius

Small:
10px

Medium:
14px

Large:
18px

XL:
24px

Pill:
999px

Use moderate rounding.
Avoid making every component excessively pill-shaped.

---

## 06 — Shadows

Small:

0 2px 8px rgba(2,20,8,.05)

Medium:

0 10px 30px rgba(2,20,8,.07)

Large:

0 18px 50px rgba(2,20,8,.10)

Shadow should establish hierarchy, not decoration.

---

## 07 — Layout

Admin:

Sidebar + Topbar + Main content

Desktop sidebar:
256–280px

Main content:
fluid with max-width around 1440–1500px

Mobile:
sidebar becomes drawer/off-canvas navigation

Public:

Header
Hero
Content sections
CTA
Footer

Booking:

Progress / context
Service
Date & time
Customer data
Review
Confirmation

---

## 08 — Sidebar

Background:

#021408

Primary active indicator:

#8BC53D

Text:
white / muted green-white

Active state should be clear without relying on color alone.

Use:

- icon
- label
- active indicator
- optional badge

Do not use bright gradient backgrounds.

---

## 09 — Topbar

Background:
#FFFFFF

Border:
#DCE6D7

Optional subtle blur only when it improves hierarchy.

Topbar contains:

- Page title
- Context / breadcrumb
- Notifications
- Profile / admin controls

Avoid oversized headers.

---

## 10 — Buttons

Primary:

Background #8BC53D
Text #022F12

Hover:
darker / stronger green

Secondary:

Background #FFFFFF
Border #DCE6D7
Text #022F12

Ghost:

Transparent
Text #022F12

Danger:

Use semantic danger only.

Minimum practical touch target:
44 × 44px

Every interactive button needs:

- hover
- focus-visible
- active
- disabled

---

## 11 — Cards

Default card:

Background #FFFFFF
Border #DCE6D7
Radius 16–18px
Subtle shadow

Do not put every piece of information in a separate card.

Use visual grouping instead.

---

## 12 — Forms

Inputs:

- clear label
- 44px+ comfortable touch height
- visible focus state
- error state
- helper text when necessary
- correct RTL alignment

Never rely only on placeholder text.

---

## 13 — Tables

Tables should prioritize:

1. readability
2. scanning
3. status visibility
4. actions

Use:

- sticky header when useful
- row hover
- consistent numeric alignment
- status badges
- action menu

Avoid excessive borders.

---

## 14 — Status Badges

Examples:

Pending
Confirmed
Completed
Cancelled
Blocked
Available

Status must communicate through:

- text
- icon where useful
- color

Never color-only.

---

## 15 — Calendar / Booking

Calendar must optimize for:

- date clarity
- available slots
- unavailable slots
- current date
- selected date
- confirmation

Selected state:

Primary green background / high contrast.

Unavailable:

Muted + disabled interaction.

Do not communicate availability using color alone.

---

## 16 — Booking UX

Flow:

1. Select service
2. Select date
3. Select time
4. Customer details
5. Review
6. Confirmation

User should always know:

- current step
- previous step
- next action
- selected information

Avoid unnecessary scrolling.

---

## 17 — Feedback States

Every async operation should provide feedback.

Required states:

Loading
Success
Error
Empty
Disabled

Use skeletons where useful.

Do not leave the interface apparently frozen.

---

## 18 — Mobile

Mobile is a primary layout.

Requirements:

- minimum 44px touch targets
- no horizontal page scrolling
- readable 15–16px body text
- accessible forms
- drawer navigation for admin
- stacked cards only when useful
- fixed CTA only when it improves conversion/usability

---

## 19 — Accessibility

Minimum requirements:

- visible keyboard focus
- sufficient contrast
- semantic HTML
- labels for inputs
- accessible names for icon buttons
- logical RTL reading order
- status not communicated by color alone
- reduced-motion support where relevant

---

## 20 — Motion

Motion should communicate:

- state change
- navigation
- hierarchy
- feedback

Default duration:

150–220ms

Use transform/opacity where possible.

Avoid:

- constant animations
- bouncing UI
- decorative motion
- excessive parallax

---

## 21 — Iconography

Use one coherent icon family.

Icons must:

- have consistent stroke/fill style
- align with text
- have accessible labels when interactive

Do not mix unrelated icon styles.

---

## 22 — Component Priority

Build in this order:

1. Design tokens
2. Typography
3. Sidebar
4. Topbar
5. Buttons
6. Form controls
7. Cards
8. Tables
9. Status badges
10. Calendar
11. Modals
12. Toasts
13. Empty states
14. Loading states

---

## 23 — CSS Architecture

There must be ONE authoritative Green Vita token layer.

Preferred structure:

foundation
↓
tokens
↓
global primitives
↓
components
↓
page-specific styles

Do NOT create another final.css / redesign.css / theme-v2.css layer.

Existing legacy CSS remains untouched until audited and migrated.

---

## 24 — Legacy CSS Migration

Current legacy styles include:

- admin.css
- dashboard-redesign.css
- gv-luxury-theme.css
- gv-modern-admin.css
- green-vita-ui.css
- green-vita-final.css
- booking-prototype.css
- public-shared-header.css

These files are NOT deleted immediately.

Migration strategy:

1. Inventory
2. Identify reusable rules
3. Map rules to tokens/components
4. Move required rules
5. Switch page references
6. Visual review
7. Remove obsolete rules only after verification

---

## 25 — Page Design Order

Admin:

1. Dashboard
2. Reservations
3. Visits
4. Calendar / Booking
5. Smart Bio
6. Visit details
7. Login

Public:

1. Home
2. Services
3. Booking
4. About
5. Contact

---

## 26 — Green Vita Visual Principle

The interface should feel like:

"یک کلینیک تخصصی گیاه‌پزشکی مدرن و لوکس"

Not:

"یک داشبورد سبز معمولی"

Visual hierarchy must always favor:

Clarity
→ Trust
→ Action
→ Brand character

---

## 27 — Definition of Done

A page is not complete until:

- responsive
- RTL correct
- typography consistent
- tokens used
- focus states visible
- hover states defined
- loading state handled
- empty state handled
- error state handled
- semantic status
- no unnecessary duplication
- no broken overflow
- no visual conflict with global theme

---

## 28 — Current Approved Palette

Primary:
#8BC53D

Primary Dark:
#022F12

Sidebar:
#021408

Background:
#F7FAF2

Surface:
#FFFFFF

Soft:
#E4F0CC

Gold:
#C6A15B

Gold Soft:
#E8D8B5

Text:
#021408

Text Soft:
#496054

Muted:
#7C8B82

Border:
#DCE6D7

---

Version:
1.0

Status:
Design foundation approved for implementation.

