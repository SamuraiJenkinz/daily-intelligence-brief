---
phase: 16-dashboard-config-updates
plan: 02
subsystem: presentation-layer
tags: [templates, ui-simplification, factiva, badge-rendering, source-management]
status: complete
completed: 2026-02-27

# Dependency graph
requires:
  - "15-03-PLAN.md (Apify cleanup, SourceType model updates)"
  - "16-01-PLAN.md (Dashboard run source simplified to Factiva-only)"
provides:
  - "Factiva-only badge rendering in all user-facing templates"
  - "Simplified source management UI (Name, URL, Status, Actions)"
affects:
  - "Future template development (no Apify/RSS conditional logic needed)"

# Tech tracking
tech-stack:
  added: []
  removed: ["Apify badge rendering", "RSS badge rendering", "Source type dropdown", "Actor ID field"]
  patterns: ["Simplified conditional logic", "Factiva-only branding"]

# File tracking
key-files:
  created: []
  modified:
    - path: "app/templates/role_brief.html"
      change: "Replaced if/else badge logic with Factiva-only rendering"
    - path: "app/templates/email/role_email.html"
      change: "Replaced if/else badge logic with Factiva-only rendering"
    - path: "app/templates/admin/partials/search_results.html"
      change: "Replaced if/elif badge logic with Factiva-only rendering"
    - path: "app/templates/admin/partials/source_form.html"
      change: "Removed type dropdown and actor_id field, simplified to Name/URL/Status"
    - path: "app/templates/admin/partials/source_edit_row.html"
      change: "Removed type and actor_id cells, 4-column layout"
    - path: "app/templates/admin/partials/source_row.html"
      change: "Removed type badge and actor_id code cells, 4-column layout"
    - path: "app/templates/admin/sources.html"
      change: "Updated table headers to Name/URL/Status/Actions, removed .badge-type CSS"

# Decisions
decisions:
  - id: "template-badge-simplification"
    context: "All articles in fresh DB are Factiva-sourced, no historical Apify/RSS data"
    decision: "Replace conditional badge rendering with Factiva-only badges across all templates"
    rationale: "Simpler template logic, consistent branding, reflects current reality as Factiva-only system"
    alternatives_considered: ["Keep conditional logic for potential future sources", "Remove badges entirely"]
    outcome: "Clean templates with no Apify/RSS rendering paths, reduced complexity"

  - id: "source-ui-simplification"
    context: "Source type and actor_id are legacy concepts from Apify days, no longer needed for Factiva-only system"
    decision: "Remove type and actor_id fields from source management UI, simplify to Name/URL/Status/Actions"
    rationale: "UI should reflect reality that all sources are Factiva-based, reduce user confusion"
    alternatives_considered: ["Keep fields as read-only", "Hide fields with CSS", "Keep for potential future expansion"]
    outcome: "Clean 4-column source management UI, reduced cognitive load for admins"

# Metrics
metrics:
  files_modified: 7
  lines_removed: 85
  lines_added: 6
  duration: "2 minutes"
  deviations: 0
---

# Phase 16 Plan 02: Template Badge & UI Simplification Summary

**One-liner:** Remove Apify/RSS badge rendering from all templates and simplify source management UI to Factiva-only model (Name, URL, Status, Actions).

## Objective Achieved

Cleaned all user-facing templates to show Factiva-only badges and simplified source management UI by removing legacy type and actor_id fields.

**Purpose:** All articles are Factiva-sourced (fresh DB, no historical Apify data). Templates should reflect this reality with simplified badge rendering and source management should reflect that source type and actor_id are legacy concepts.

## Tasks Completed

### Task 1: Remove Apify/RSS badge rendering from brief, email, and search templates ✅
**Commit:** e17ab44

**Changes:**
- `app/templates/role_brief.html` (lines 740-744): Replaced if/else conditional with single Factiva badge when collector_source exists
- `app/templates/email/role_email.html` (lines 137-141): Replaced if/else conditional with single Factiva badge when collector_source exists
- `app/templates/admin/partials/search_results.html` (lines 35-43): Replaced if/elif conditional with single Factiva badge when collector_source exists

**Verification:**
- ✅ `grep -c "Apify" app/templates/role_brief.html` → 0
- ✅ `grep -c "Apify" app/templates/email/role_email.html` → 0
- ✅ `grep -ci "rss" app/templates/admin/partials/search_results.html` → 0

### Task 2: Simplify source management UI (remove type and actor_id) ✅
**Commit:** ebe4b34

**Changes:**
- `app/templates/admin/partials/source_form.html`: Removed type dropdown (lines 38-53) and actor_id field (lines 55-65), moved Status to new row
- `app/templates/admin/partials/source_edit_row.html`: Removed type dropdown cell (lines 26-37) and actor_id cell (lines 39-46)
- `app/templates/admin/partials/source_row.html`: Removed type badge cell (lines 11-16) and actor_id code cell (lines 17-23)
- `app/templates/admin/sources.html`: Removed "Type" and "Actor ID" table headers (lines 115-116), removed .badge-type CSS (lines 27-30)

**Verification:**
- ✅ `grep -ci "source_type|actor_id|apify|newSourceType|newSourceActorId" app/templates/admin/partials/source_form.html` → 0
- ✅ `grep -ci "source_type|actor_id|apify" app/templates/admin/partials/source_edit_row.html` → 0
- ✅ `grep -ci "source_type|actor_id|apify|rss" app/templates/admin/partials/source_row.html` → 0
- ✅ `grep -c "Type|Actor ID" app/templates/admin/sources.html` → 0

## Deviations from Plan

None - plan executed exactly as written.

## Technical Details

### Badge Rendering Pattern (Before → After)

**Before:**
```jinja2
{% if article.collector_source == 'Factiva' %}
<span style="...">via Factiva</span>
{% else %}
<span style="...">via Apify/RSS</span>
{% endif %}
```

**After:**
```jinja2
{% if article.collector_source %}
<span style="...">via Factiva</span>
{% endif %}
```

### Source Management Layout (Before → After)

**Before:** 6-column table (Name | URL | Type | Actor ID | Status | Actions)
**After:** 4-column table (Name | URL | Status | Actions)

**Form Before:** Name, URL, Type dropdown, Actor ID field, Status toggle
**Form After:** Name, URL, Status toggle (clean 2-row layout)

## Success Criteria Met

- ✅ Zero Apify/RSS references in any template file under app/templates/ (except factiva.html documentation)
- ✅ Brief and email templates render Factiva badge for all articles
- ✅ Source forms have only Name, URL, and Status fields
- ✅ Source table shows only Name, URL, Status, and Actions columns

## Testing Evidence

### Template Badge Rendering
```bash
# All user-facing templates clean
grep -rn "Apify\|apify" app/templates/
# Returns only: app/templates/admin/factiva.html:162 (documentation text)

# No RSS badge rendering
grep -rn "bi-rss" app/templates/
# Returns: 0 matches
```

### Source Management UI
```bash
# No type or actor_id fields in forms
grep -rn "source_type\|actor_id" app/templates/admin/partials/
# Returns: 0 matches (only in non-partial files like factiva.html settings)

# Table headers simplified
grep "th>Name\|th>URL\|th>Status\|th>Actions" app/templates/admin/sources.html
# Returns: 4 matches (clean 4-column layout)
```

## Impact Analysis

### User Experience
- **Admins:** Simplified source creation form, fewer fields to understand
- **Email Recipients:** Consistent Factiva branding on all articles
- **Brief Readers:** Consistent Factiva branding on all articles
- **Search Users:** Clean Factiva badge only, no secondary badge confusion

### Code Maintainability
- **Reduced complexity:** No more conditional badge logic to maintain
- **Future-proof:** Adding new sources only requires updating single badge logic (if needed)
- **Consistent:** All templates use same badge rendering pattern

### Performance
- Negligible impact (removed a few conditional checks per article render)

## Next Phase Readiness

**Phase 16 Status:** 2/3 plans complete
- ✅ 16-01: Dashboard run source simplified
- ✅ 16-02: Template badge & UI simplified (this plan)
- ⏳ 16-03: Settings page cleanup (remaining)

**Blockers:** None

**Concerns:** None - templates now accurately reflect Factiva-only reality

**Database State:** Fresh (no historical Apify articles to cause badge rendering confusion)

## Lessons Learned

1. **Template Auditing:** Systematic grep across all templates revealed exact locations for badge rendering updates
2. **UI Simplification:** Removing unused fields improved admin UX without impacting functionality
3. **Consistent Patterns:** All three badge locations (brief, email, search) used same if/else pattern → easy to replace consistently

## Files Changed

**Modified (7 files):**
1. `app/templates/role_brief.html` - Factiva-only badge
2. `app/templates/email/role_email.html` - Factiva-only badge
3. `app/templates/admin/partials/search_results.html` - Factiva-only badge
4. `app/templates/admin/partials/source_form.html` - Removed type & actor_id fields
5. `app/templates/admin/partials/source_edit_row.html` - Removed type & actor_id cells
6. `app/templates/admin/partials/source_row.html` - Removed type & actor_id columns
7. `app/templates/admin/sources.html` - Updated headers, removed CSS

## Commits

1. `e17ab44` - refactor(16-02): remove Apify/RSS badge rendering from templates
2. `ebe4b34` - refactor(16-02): simplify source management UI (remove type and actor_id)

**Total Duration:** 2 minutes
**Total Commits:** 2 (atomic per-task commits)
