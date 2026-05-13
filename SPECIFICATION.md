# Hospitality Talent Cloud — Product Specification

> **Audience.** This document is the single source of truth for the recruitment
> portal. It is written in plain language so that a business owner, hiring
> manager, or HR director can read, edit, and clarify any requirement without
> needing a developer. Every requirement is numbered (REQ-XXX) so that
> conversations and tickets can refer back to a specific line.
>
> **How to edit.** Open this file, find the requirement number, change the
> wording. If a requirement no longer applies, strike it through with
> `~~text~~`. If a new one is needed, add it at the bottom of its section using
> the next free number.

---

## 1. Vision

A bold, visual recruitment portal that any hotel group can plug into. Each
group uploads its own talent pipeline once, and from then on the portal becomes
the single window into every candidate, every open role, and every hire across
every property the group operates.

**Tagline.** *"From CV to check-in — one pipeline for every property."*

**Primary outcomes we are optimising for**

1. **Speed-to-hire.** A General Manager seeing a roster gap on Monday should
   have a shortlist on Tuesday.
2. **Visibility.** A Group HR Director should see, on one screen, the health of
   the talent pipeline across every brand and every region.
3. **Re-use of talent.** A candidate rejected for a role in Property A should
   surface automatically when a similar role opens in Property B.
4. **Brand confidence.** The portal must feel as polished as the hotels it
   serves — bold, calm, and obviously premium.

---

## 2. Who Uses the Portal

| Persona              | What they need from the portal                                                  |
|----------------------|---------------------------------------------------------------------------------|
| Group HR Director    | Group-wide metrics, benchmarking between properties, board-ready exports.       |
| Property HR Manager  | Day-to-day pipeline management for their hotel, requisition approval.           |
| Hiring Manager (HoD) | Reviewing shortlists, leaving feedback on interviews, requesting new roles.     |
| Recruiter / Sourcer  | Uploading CVs in bulk, searching the pipeline, moving candidates between stages.|
| Candidate (external) | A public apply-page per role and a status portal to track their application.    |
| Auditor / Compliance | Read-only access with a clear audit trail of every action.                      |

- **REQ-001.** The portal shall support all six personas above out of the box.
- **REQ-002.** Each persona shall see only the data and actions appropriate to
  their role (see Section 11, Permissions).

---

## 3. Multi-Tenancy — One Portal, Many Hotel Groups

The platform is sold to hotel groups. Each group is a **tenant**. Each tenant
operates **properties** (individual hotels) and **brands** (sub-collections of
properties, e.g. luxury vs. select-service).

- **REQ-010.** A tenant's data shall be fully isolated from every other
  tenant's data. No user from Tenant A shall ever see a record from Tenant B.
- **REQ-011.** A tenant shall be able to model an unlimited number of
  properties and brands underneath it.
- **REQ-012.** A user may belong to one tenant only. (If a person works for
  two groups, they have two logins.)
- **REQ-013.** A tenant administrator shall be able to customise:
  - the tenant's logo, colour palette, and display name shown in the header,
  - the list of pipeline stages (see Section 5),
  - the list of properties and brands,
  - the list of standard role templates (e.g. *Front Office Agent*, *Sous Chef*).
- **REQ-014.** A tenant shall be able to switch between properties or view
  "All properties" from a property-selector in the top bar.
- **REQ-015.** Onboarding a new tenant shall take no more than 30 minutes
  from contract signature to first user login.

---

## 4. Bringing Existing Talent Into the Portal

Most hotel groups already have a talent pipeline somewhere — a spreadsheet, a
legacy ATS, a folder of CVs. The portal must absorb that pipeline cleanly.

- **REQ-020.** The portal shall accept candidate data via **four** channels:
  1. **CSV / Excel upload** (drag-and-drop, up to 50,000 rows per file).
  2. **Bulk CV upload** (PDF / DOCX, parsed automatically into structured data).
  3. **API import** from another ATS (Workday, Greenhouse, Lever, SmartRecruiters,
     Oracle HCM — at minimum).
  4. **Manual single-candidate entry** via a form.
- **REQ-021.** During CSV import the portal shall present an interactive
  **field-mapping screen** so that the business user can map their column
  headers (e.g. "Full Name", "Email Address") to the portal's canonical fields.
- **REQ-022.** Field mappings shall be saved per tenant so that subsequent
  uploads of the same format require zero re-mapping.
- **REQ-023.** Duplicate detection shall run on every import. The default rule
  is *same email OR same phone number*. The tenant admin may change this rule.
- **REQ-024.** When a duplicate is detected, the portal shall offer three
  options: *Skip*, *Merge into existing record*, or *Create new record anyway*.
- **REQ-025.** Every import shall produce a downloadable **import report**
  listing rows accepted, rows skipped, rows merged, and rows that failed
  validation, with the reason for each failure.
- **REQ-026.** CV parsing accuracy shall be measurable; the portal shall flag
  any extracted field with confidence below 80% for human review before the
  candidate is added to the active pipeline.

---

## 5. The Talent Pipeline

The pipeline is the spine of the product. A candidate moves through stages;
the portal makes that movement obvious, measurable, and reversible.

### 5.1 Default stages

1. **Sourced** — candidate is in the system but has not yet been actively
   considered for a specific role.
2. **Screened** — recruiter has reviewed the candidate against a role.
3. **Interview** — at least one interview has been scheduled or completed.
4. **Offer** — an offer has been extended.
5. **Hired** — offer accepted and start date confirmed.
6. **Talent Pool** — not progressing on the current role but kept warm for future.
7. **Rejected / Withdrawn** — closed for now, with a reason.

- **REQ-030.** A tenant admin may rename, reorder, hide, or add custom stages.
  *Sourced* and *Hired* may not be deleted.
- **REQ-031.** Each candidate-on-a-role shall have exactly one current stage.
- **REQ-032.** Every stage change shall be logged with timestamp, actor, and
  reason. The audit log is immutable.
- **REQ-033.** Moving a candidate backwards (e.g. Offer → Interview) shall be
  allowed but shall require a reason from a controlled list.
- **REQ-034.** A candidate may exist in the pipeline for **multiple roles
  simultaneously**, and their stage on each role is tracked independently.

### 5.2 Kanban view

- **REQ-035.** The pipeline shall be presented as a horizontal kanban board
  with one column per stage.
- **REQ-036.** Each card on the kanban shall show: candidate name (or initials
  if photo unavailable), role applied for, property, recruiter avatar, days in
  current stage, and a single colour-coded fit-score (0–100).
- **REQ-037.** Cards shall be draggable between columns. Drop = stage change.
- **REQ-038.** If a card has been in its current stage for longer than the
  configured *time-in-stage* threshold (default: 7 days), it shall be visually
  highlighted as stale.

### 5.3 Group-level pipeline view

- **REQ-040.** A Group HR Director shall be able to view the pipeline for one
  property, several properties, one brand, or the entire group.
- **REQ-041.** Aggregated views shall always show the number of properties
  contributing to the figures shown, and shall warn if any property has
  incomplete data.

---

## 6. Finding the Right Person — Search & Discovery

- **REQ-050.** A global search bar shall be present on every page and shall
  search across candidates, jobs, and properties simultaneously.
- **REQ-051.** Search shall match across name, email, phone, skills, current
  employer, previous employer, languages spoken, and certifications.
- **REQ-052.** Search shall be **fuzzy** — minor spelling variations and
  diacritics shall not prevent a match.
- **REQ-053.** Users shall be able to combine filters: property, role family,
  stage, language, location radius from a property, salary expectation,
  notice period, right-to-work status, and tags.
- **REQ-054.** Any filtered view shall be **saveable** as a private or shared
  shortlist (e.g. "Bilingual front-office talent near our Lisbon property").
- **REQ-055.** The portal shall surface a *"Similar candidates"* suggestion
  block on every candidate profile — other people in the pipeline who match
  the same role family, skills, or location.

---

## 7. Dashboard, Metrics & Reporting

The dashboard is the first screen a user sees after login. It must answer the
question *"what does my pipeline look like today?"* in under five seconds.

### 7.1 Top-line metrics (always visible)

- **REQ-060.** **Active candidates** — total count of candidates not in
  *Rejected* or *Hired* stages.
- **REQ-061.** **Open roles** — count of approved requisitions not yet filled.
- **REQ-062.** **Time-to-hire (rolling 90 days)** — median days from *Sourced*
  to *Hired* for hires made in the last 90 days.
- **REQ-063.** **Offer acceptance rate (rolling 90 days)** — accepted offers /
  total offers extended.

### 7.2 Visualisations

- **REQ-070.** A **funnel chart** shall show conversion between every stage,
  with the absolute count and the conversion % between adjacent stages.
- **REQ-071.** A **source breakdown** (donut chart) shall show where hires
  came from (referral, agency, career site, LinkedIn, internal mobility, etc.).
- **REQ-072.** A **hires-by-property** bar chart shall compare hire volume
  across all properties in the selected scope.
- **REQ-073.** A **time-in-stage heatmap** shall identify bottlenecks — which
  stage is each property losing candidates in?
- **REQ-074.** All charts shall be exportable as PNG or CSV.

### 7.3 Live activity & spotlights

- **REQ-080.** A **recent activity feed** shall show the last 20 events
  (stage changes, new applications, offers extended) in the selected scope.
- **REQ-081.** A **top candidates spotlight** shall feature the five
  highest-scoring candidates currently in *Screened* or *Interview*, so that
  busy managers see standouts without searching.

### 7.4 Scheduled reports

- **REQ-085.** Any user may schedule a daily, weekly, or monthly email of any
  dashboard view.
- **REQ-086.** The Group HR Director shall receive a *board-ready PDF*
  automatically on the first working day of each month.

---

## 8. Job Requisitions

- **REQ-090.** A hiring manager shall be able to raise a requisition from a
  role template, specifying property, headcount, salary band, start date, and
  required skills.
- **REQ-091.** Requisitions shall route through a configurable approval chain
  (default: Property HR → Property GM → Group HR for any salary above band).
- **REQ-092.** Approved requisitions shall publish automatically to the
  candidate-facing careers site and to any connected job boards (Indeed,
  LinkedIn Jobs).
- **REQ-093.** Time-to-fill shall be tracked per requisition.

---

## 9. Interviews & Communication

- **REQ-100.** The portal shall support video, phone, and on-property
  interview formats.
- **REQ-101.** Calendar integration shall be available for Google Workspace
  and Microsoft 365 at launch.
- **REQ-102.** Interviewers shall complete a structured scorecard per
  interview; free-text-only feedback is not permitted.
- **REQ-103.** Candidates shall receive automated status emails at every stage
  change. Templates shall be editable per tenant and translatable into at
  least eight languages.
- **REQ-104.** A candidate shall be able to log in to a lightweight **candidate
  status portal** to see their stage, scheduled interviews, and any actions
  required of them.

---

## 10. Onboarding the Hire

- **REQ-110.** When a candidate reaches *Hired*, the portal shall trigger a
  configurable onboarding workflow (e.g. send offer letter, request right-to-
  work documents, create email account via HRIS integration).
- **REQ-111.** Onboarding workflows shall be tenant-editable without
  developer involvement.

---

## 11. Roles & Permissions

- **REQ-120.** Permissions shall be enforced both in the UI and on the API.
- **REQ-121.** The default roles are:
  - **Tenant Admin** — full access within their tenant.
  - **Group HR** — read/write all properties.
  - **Property HR** — read/write candidates linked to their property.
  - **Hiring Manager** — read/write candidates linked to their open
    requisitions only.
  - **Recruiter / Sourcer** — as Property HR, plus the ability to upload.
  - **Auditor** — read-only across the entire tenant.
- **REQ-122.** Custom roles shall be creatable by combining atomic permissions
  (read-candidate, edit-candidate, advance-stage, extend-offer, export-data,
  etc.).
- **REQ-123.** Sensitive fields (salary expectation, right-to-work documents,
  protected characteristics) shall be hideable on a per-role basis.

---

## 12. Privacy, Compliance & Data Residency

- **REQ-130.** Personal data shall be handled in accordance with GDPR (EU),
  POPIA (South Africa), and CCPA (California) at minimum.
- **REQ-131.** A candidate shall be able to request export and erasure of
  their data via a self-service link in any status email.
- **REQ-132.** Each tenant shall choose a data-residency region at
  contract-signing (EU, UK, US, APAC, ZA). Data shall not leave that region
  except for explicitly opted-in features.
- **REQ-133.** Candidate records shall auto-archive after a tenant-configurable
  retention period (default: 24 months of inactivity), and shall be hard-
  deleted after a further 6 months unless legally required to retain.
- **REQ-134.** All actions touching personal data shall be written to an
  immutable audit log retained for 7 years.

---

## 13. Integrations

- **REQ-140.** The portal shall expose a documented REST API and webhooks for
  every key event (candidate created, stage changed, offer extended, hire
  confirmed).
- **REQ-141.** Pre-built integrations at launch: Workday, Greenhouse, Lever,
  SmartRecruiters, Oracle HCM, BambooHR, LinkedIn Jobs, Indeed, Google
  Workspace, Microsoft 365, DocuSign.
- **REQ-142.** A pre-built integration shall require no more than three
  clicks from the tenant admin to enable.

---

## 14. Look, Feel & Interaction Principles

The brand of the portal is **calm, confident, premium** — a tool a luxury
hotel group is proud to put on their HR Director's desk.

- **REQ-150.** Typography shall be a single modern sans-serif (Inter or
  equivalent) with strong weight contrast.
- **REQ-151.** The palette is deep ink (near-black), warm champagne gold as
  the primary accent, and a single secondary accent per tenant (configurable).
- **REQ-152.** Every page shall load actionable content above the fold on a
  1366×768 laptop screen.
- **REQ-153.** Every dataset on screen shall be interactive — clickable
  numbers drill down, charts respond to hover, lists are searchable.
- **REQ-154.** No data table shall exceed seven columns by default; additional
  columns shall be opt-in via a column-picker.
- **REQ-155.** The portal shall be fully responsive down to a 375px screen
  width (iPhone SE).
- **REQ-156.** Light and dark theme shall both be supported, defaulting to the
  user's OS preference.
- **REQ-157.** All non-text controls shall have an accessible label;
  WCAG 2.2 AA shall be the minimum bar.

---

## 15. Non-Functional Requirements

- **REQ-160.** First-Contentful-Paint shall be under 1.5 seconds on a
  10 Mbps connection.
- **REQ-161.** The dashboard shall handle a tenant of up to 500,000 candidate
  records and 200 properties without degradation.
- **REQ-162.** Uptime SLA shall be 99.9% measured monthly.
- **REQ-163.** All data at rest shall be AES-256 encrypted; all data in
  transit shall be TLS 1.3.
- **REQ-164.** Daily encrypted backups shall be retained for 35 days; restore
  RTO is 4 hours, RPO is 1 hour.

---

## 16. Acceptance Criteria for v1 Launch

A tenant is considered "successfully launched" when **all** of the following
are true:

- [ ] Tenant branding (logo, colour, name) is applied across every screen.
- [ ] At least one property and one brand are configured.
- [ ] At least 100 candidates have been imported, with import-report errors
      resolved.
- [ ] At least one role template, one requisition, and one approved
      requisition exist.
- [ ] At least three user accounts are provisioned across at least two roles.
- [ ] One candidate has been moved end-to-end from *Sourced* to *Hired* in
      a guided walkthrough.
- [ ] The Group HR Director has received and signed off on a sample monthly
      PDF report.

---

## 17. Out of Scope for v1

To keep v1 focused, the following are explicitly **not** in scope and will be
considered for v2:

- Payroll integration.
- Time-and-attendance.
- Learning-management / training records.
- AI-generated interview questions (research spike only in v1).
- Native mobile apps (the responsive web app is the v1 mobile experience).

---

## 18. Open Questions for the Business Owner

These are decisions only the business can make. Please answer inline.

1. **Pricing model** — per-property, per-active-candidate, or per-seat?
   *Answer:* _____________________________________________________________
2. **Default data-residency region** for new tenants if not specified?
   *Answer:* _____________________________________________________________
3. **Languages required at launch** beyond English?
   *Answer:* _____________________________________________________________
4. **Reference tenants** we can use as design partners for v1?
   *Answer:* _____________________________________________________________
5. **Brand name** of the product itself — *Hospitality Talent Cloud* is a
   placeholder.
   *Answer:* _____________________________________________________________

---

## 19. Glossary

- **Tenant** — a hotel group that licenses the portal.
- **Property** — an individual hotel operated by a tenant.
- **Brand** — a collection of properties under one customer-facing identity.
- **Requisition** — an approved open role to be filled.
- **Pipeline** — the sequence of stages a candidate moves through.
- **Talent Pool** — candidates retained for future roles, not currently
  active on any requisition.
- **Fit-score** — a 0–100 composite of how well a candidate matches a role
  (skills + experience + location + availability).

---

## 20. Change Log

| Date       | Author | Change                                  |
|------------|--------|-----------------------------------------|
| 2026-05-13 | Initial draft | First end-to-end spec for v1.   |
