# Section 508 / WCAG 2.2 Accessibility Compliance Report

**Application:** EarthRISE Applied AI & Deep Learning Book (Django)
**Date:** 2026-07-27
**Standard:** WCAG 2.2 Level A and Level AA (maps to Section 508 / 36 CFR Part 1194)
**Testing Tools:** pa11y 9.1.1 with htmlcs runner + axe-core 4.11 runner
**Browser:** Chromium 151.0.7922.47 (via Puppeteer)
**Server:** Django 6.0.6, localhost:8080

---

## 1. Executive Summary

Automated accessibility testing was performed on 7 pages of this application using both the **HTML_CodeSniffer (htmlcs)** and **axe-core** engines via pa11y 9.1.1. Testing was conducted against the **WCAG2AA** standard, which covers all WCAG 2.2 Level A and Level AA success criteria and directly corresponds to Section 508 requirements.

**Overall Compliance Status: NON-COMPLIANT**

The application has confirmed violations at **WCAG Level A** (the minimum baseline), which constitutes a failure to meet Section 508 requirements. Critical issues affect every page via the shared `base.html` template, and severe issues exist in notebook-rendered chapter content.

### Summary of Confirmed Errors by Page

| Page | htmlcs Errors | axe Errors | htmlcs Warnings | Status |
|---|---|---|---|---|
| Home (`/`) | 30 | 21 | 25 | **FAIL** |
| Chapter: data-preparation | 2 | 0 | 10 | **FAIL** |
| Chapter: crop-mapping | 672 | 635 | 190 | **FAIL** |
| Chapter: object-detection | 2 | 0 | 10 | **FAIL** |
| Chapter: ethics-of-ai | 2 | 0 | 10 | **FAIL** |
| Chapter: conclusions | 2 | 0 | 10 | **FAIL** |
| 404 page | 0 | 0 | 1 | **PASS** (errors only) |

> **Note:** The `chapter-crop-mapping` page contains a heavily-rendered Jupyter notebook. The majority of its errors (341 empty anchors, 288+ contrast failures) originate from Quarto/nbconvert-generated HTML within the notebook content, not from the Django application shell.

---

## 2. Test Methodology

### Tools and Configuration
- **pa11y 9.1.1** — CLI accessibility testing framework
- **Runner 1: htmlcs** (HTML_CodeSniffer) — tests against WCAG 2.2 rules using pattern matching and DOM inspection
- **Runner 2: axe-core 4.11** — Deque's widely adopted engine, used as the authoritative second source
- **Standard:** `WCAG2AA` — covers Level A and Level AA success criteria
- **Wait time:** 2000ms after page load before testing (allows JavaScript to render)
- **Scope:** Full page (no elements excluded)
- **Options:** `includeNotices: true`, `includeWarnings: true` (all issue types captured)

### Pages Tested

| Template | URL | Description |
|---|---|---|
| `home.html` | `/` | Introduction / landing page |
| `chapter.html` | `/chapter/data-preparation/` | Typical chapter (markdown content) |
| `chapter.html` | `/chapter/crop-mapping/` | Heavy notebook-rendered chapter |
| `chapter.html` | `/chapter/object-detection/` | Typical chapter |
| `chapter.html` | `/chapter/ethics-of-ai/` | Typical chapter |
| `chapter.html` | `/chapter/conclusions/` | Typical chapter |
| `404.html` | `/nonexistent-page/` | Error page |

### Tooling Notes
- htmlcs reports **notices** (manual checks recommended) and **warnings** (likely issues) in addition to confirmed errors
- axe reports **violations** (errors) and **needs-review** items (warnings); it does not generate notices
- Both engines were run separately to maximize coverage; issues may overlap between runners
- Results reflect the application state at test time with Django `DEBUG=True`

---

## 3. Confirmed Violations by WCAG Success Criterion

### 3.1 WCAG 1.1.1 — Non-text Content (Level A)
**Section 508:** §1194.22(a) — *"A text equivalent for every non-text element shall be provided via "alt", "longdesc", or in element content."*

**Status: FAIL**

Images on the home page are missing `alt` attributes, making them inaccessible to screen reader users.

| Issue | Count | Tool | Selector / Context |
|---|---|---|---|
| `<img>` missing `alt` attribute | 4 | htmlcs (H37) | Book cover image; author photo images (Tim, Biplov, David) |
| Image-only link missing alt text on `<img>` | 6 | htmlcs (H30.2) | ORCID icon links for all three authors (×2 occurrences per author) |
| Images without alt text | 9 | axe (image-alt) | Same images + ORCID icons |
| Image-only links with no discernible text | 6 | axe (link-name) | ORCID href links containing only unlabeled `<img>` |

**Affected pages:** Home (`/`) and any chapter containing author blocks
**Root cause:** Quarto-generated HTML for author/editor sections does not include `alt` attributes on author photos or ORCID badge icons

**Fix:** Add `alt` text to every affected `<img>`:
```html
<!-- Author photos -->
<img src="Tim_img_410_410.png" alt="Tim Dye, Editor" width="200">
<img src="Biplov_img_410_410.png" alt="Biplov Bhandari, Editor" width="200">
<img src="David_img_400_410.png" alt="David Lagomasino, Editor" width="200">

<!-- ORCID links -->
<a href="https://orcid.org/0000-0001-9489-9392">
  <img src="https://orcid.org/sites/default/files/images/orcid_16x16.png"
       alt="ORCID profile for Tim Dye">
</a>
```

---

### 3.2 WCAG 1.3.1 — Info and Relationships (Level A)
**Section 508:** §1194.22(n) — *"When electronic forms are designed to be completed on-line, the form shall allow people using assistive technology to access the information, field elements, and functionality required for completion and submission of the form."*

**Status: FAIL**

The chat widget's `<textarea>` in `base.html` has no accessible label. This affects **every page** in the application.

| Issue | Count | Tool | Selector |
|---|---|---|---|
| Textarea has no accessible name (no label, title, aria-label, aria-labelledby) | 1 | htmlcs (H91.Textarea.Name) | `#chatInput` |
| Form field not labeled | 1 | htmlcs (F68) | `#chatInput` |

**Affected pages:** All pages (via `base.html`)
**Root cause:** `base.html` contains:
```html
<textarea id="chatInput" placeholder="Ask about the book…" rows="1"></textarea>
```
The `placeholder` attribute is not a substitute for an accessible label.

**Fix:** Add an `aria-label` to the textarea in `base.html`:
```html
<textarea id="chatInput"
          placeholder="Ask about the book…"
          rows="1"
          aria-label="Chat message input"></textarea>
```

---

### 3.3 WCAG 1.4.1 — Use of Color (Level A)
**Section 508:** §1194.21(i) — *"Color coding shall not be used as the only means of conveying information, indicating an action, prompting a response, or distinguishing a visual element."*

**Status: FAIL** (confirmed by axe)

Inline hyperlinks within text blocks are distinguished from surrounding text by color alone, with no underline or other non-color visual indicator.

| Issue | Count (home) | Count (crop-mapping) | Tool |
|---|---|---|---|
| Links not distinguishable without color | 4 | 14 | axe (link-in-text-block) |

**Affected pages:** Home, crop-mapping, and likely all pages with body text links
**Fix:** Add `text-decoration: underline` to links within text content, or add a bottom-border visual indicator in `horizon.css` / `notebook.css`:
```css
.chapter-content a,
#introduction a {
  text-decoration: underline;
}
```

---

### 3.4 WCAG 1.4.3 — Contrast (Minimum) (Level AA)
**Section 508:** References WCAG 2.0 Level AA contrast requirements.

**Status: FAIL** (major violations in notebook content)

Insufficient color contrast was found in two areas:

**A. Application shell (home page):**
- TOC toggle buttons (`▸` character) fail contrast requirements
- 2 failures confirmed by axe (`color-contrast`) on home page

**B. Notebook-rendered content (crop-mapping chapter):**
- 288 elements fail contrast in htmlcs (G18.Fail)
- 275 confirmed violations in axe (`color-contrast`)
- Affects: `<code>` inline elements, `<summary>` "Show code" toggles, and syntax-highlighted code block text within `<pre>` elements
- Example: `<code>notebook</code>` in a callout box; "Show code" `<summary>` elements

| Issue | Count | Tool | Location |
|---|---|---|---|
| TOC toggle insufficient contrast | 2 | axe (color-contrast) | `#chapterTocList button.chapter-toc__toggle` |
| Notebook code inline contrast failures | 288 | htmlcs (G18.Fail) | crop-mapping chapter content |
| Notebook code contrast failures | 275 | axe (color-contrast) | crop-mapping chapter content |

**Root cause:** Quarto/nbconvert-generated HTML uses syntax-highlighting color schemes (e.g., light gray on white) that do not meet the 4.5:1 ratio requirement for normal text.

**Fix:**
1. For TOC buttons: increase contrast of the `▸` toggle character in `horizon.css`
2. For notebook code: override the Quarto/nbconvert CSS color theme with a WCAG-compliant syntax highlight theme (e.g., update `notebook.css` to use accessible foreground colors for code tokens)

---

### 3.5 WCAG 1.4.10 — Reflow (Level AA)
**Status: ADVISORY WARNING** (manual verification required)

Two categories of fixed/wide content may cause two-dimensional scrolling at 320px viewport width (400% zoom equivalent):

| Issue | Count | Tool | Location |
|---|---|---|---|
| `position: fixed` elements may require 2D scroll | 2 | htmlcs (C32 warning) | Chat FAB button + chat window overlay |
| Preformatted text blocks (`<pre>`) require horizontal scroll | 69 | htmlcs (C32 warning) | crop-mapping code cells |

**Fix:**
1. Chat widget: ensure the FAB and chat window are positioned so they don't obstruct content at small viewports
2. Code blocks: add `overflow-x: auto` with `max-width: 100%` on `<pre>` elements (already partially done in `notebook.css`; verify at 320px)

---

### 3.6 WCAG 2.4.4 — Link Purpose (Level A)
**Section 508:** §1194.22(d) — *"Documents shall be organized so they are readable without requiring an associated style sheet."*

**Status: FAIL** (critical in notebook content)

Empty anchor elements (`<a href="..."></a>`) with no link text or image are present in large quantities within notebook-rendered content.

| Issue | Count | Tool | Context |
|---|---|---|---|
| Anchor element with valid href but no link content | 341 | htmlcs (H91.A.NoContent) | crop-mapping notebook code cell line numbers |
| Links with no discernible text | 343 | axe (link-name) | Same elements, including ORCID links |

**Affected pages:** crop-mapping (341 empty anchors); home (6 ORCID link-name issues)
**Root cause:** Quarto/nbconvert generates line-number anchor elements for code cells:
```html
<a href="#cb1-1"></a>  <!-- empty — line number anchor -->
<a href="#cb1-2"></a>
```
These have no visible text and no `aria-label`, making them indistinguishable to screen readers.

**Fix options:**
1. Post-process the nbconvert output to add `aria-hidden="true"` to these decorative anchors (preferred — they carry no meaningful link purpose):
   ```python
   # In convert_notebooks.py or book_ingest.py:
   from bs4 import BeautifulSoup
   soup = BeautifulSoup(html_content, 'html.parser')
   for a in soup.find_all('a', href=True):
       if not a.get_text(strip=True) and not a.find('img'):
           a['aria-hidden'] = 'true'
           a['tabindex'] = '-1'
   ```
2. Or configure Quarto/nbconvert to use a different code block rendering that omits these anchors

---

### 3.7 WCAG 4.1.1 — Parsing (Level A)
**Section 508:** §1194.22 — Valid markup is required for assistive technology compatibility.

**Status: FAIL**

Duplicate `id` attribute values appear throughout pages, violating the uniqueness requirement.

| Issue | Count (home) | Count (crop-mapping) | Tool |
|---|---|---|---|
| Duplicate id attributes | 18 | 39 | htmlcs (F77) |

**Root cause:** The TOC sidebar (in `chapter-toc.js`) reads heading IDs from the content area and may be re-rendering elements with the same IDs. Additionally, the Quarto-generated content itself has `id` attributes on headings (e.g., `id="introduction"`), and the right-side TOC navigation renders links to those same IDs — but if any element is rendered twice, the duplicate occurs.

On the home page, 18 duplicate IDs were found across all section headings (e.g., `id="introduction"`, `id="editors-introduction"`, `id="background-and-motivation"`, etc.).

**Fix:**
1. Audit how IDs are generated for the sidebar TOC — ensure `chapter-toc.js` reads existing heading IDs without creating new elements with duplicate IDs
2. If the sidebar navigation creates `<a id="...">` anchor copies, remove them and use `href="#heading-id"` links instead

---

### 3.8 WCAG 4.1.2 — Name, Role, Value (Level A)
**Section 508:** §1194.21(d) — *"Sufficient information about a user interface element including the identity, operation and state of the element shall be available to assistive technology."*

**Status: FAIL**

In addition to the chat textarea (covered in §3.2), empty anchor elements expose `<a>` elements with no accessible name to assistive technology (covered in §3.6).

---

## 4. Warnings Requiring Manual Review

The following are `warning`-level items that require human judgment to confirm or dismiss. They are not confirmed violations but indicate likely issues.

### 4.1 WCAG 1.3.1 — Heading Markup (Guideline H42, H48)

| Issue | Count | Pages | Tool |
|---|---|---|---|
| Styled text that appears to be a heading but lacks semantic heading tags | 10 (home), 1 (chapters) | All | htmlcs (H42) |
| Navigation content not marked as a list | 3 (home), 1 (chapters) | All | htmlcs (H48) |

**Recommended action:** Manually inspect the flagged elements. If visually presented as headings, wrap them in `<h2>`–`<h6>` tags. Ensure the navigation sidebar uses `<ul>/<li>` semantics.

---

### 4.2 WCAG 1.4.3 — Contrast with Transparency (G18.Alpha)

| Issue | Count | Pages | Tool |
|---|---|---|---|
| Text/background with transparency — contrast unverifiable | 6 (typical chapters), 116 (crop-mapping) | All | htmlcs (G18.Alpha) |

**Recommended action:** These are warnings because htmlcs cannot compute contrast ratios through CSS `opacity` or `rgba` transparency. Manually verify these elements meet the 4.5:1 minimum ratio against the actual rendered background.

---

### 4.3 WCAG 1.4.4 / 1.4.10 — Inline Foreground Color (F24.FGColour)

| Issue | Count | Pages | Tool |
|---|---|---|---|
| Inline foreground color set without corresponding background color | 4 | Home | htmlcs |

**Recommended action:** Review inline `style="color:..."` declarations; ensure they are accompanied by a complementary `background-color` declaration or that the inherited background is known.

---

### 4.4 Landmark Structure Issues (axe best practice warnings)

| Issue | Pages | Tool |
|---|---|---|
| Main landmark is nested inside another landmark | All | axe (landmark-main-is-top-level) |
| More than one `<main>` landmark | All | axe (landmark-no-duplicate-main) |
| Multiple landmarks with the same role and no distinguishing label | All | axe (landmark-unique) |

**Root cause (likely):** The `base.html` template wraps `<main>` inside another sectioning element, or the chat widget's container uses a `<main>` tag. The notebook content itself may also contain a `<main>` element.

**Fix:**
1. Ensure there is exactly one `<main>` element per page and it is a direct child of `<body>`
2. Label any duplicate landmark roles with `aria-label` or `aria-labelledby`
3. In `base.html`, verify the structural outline: `body > header`, `body > main`, `body > footer`

---

### 4.5 WCAG 2.4.1 — Bypass Blocks (Level A) — Manual Check Required

The htmlcs notices include a check for skip navigation links (`G1, G123, G124, H69`). No skip-to-main-content link was observed in the page source.

**Recommended action:** Add a skip navigation link at the top of `base.html`:
```html
<a href="#main-content" class="skip-link">Skip to main content</a>
<!-- ... header/nav ... -->
<main id="main-content">
```

---

### 4.6 404 Page — Table without Caption

| Issue | Count | Tool |
|---|---|---|
| Data table has no `<caption>` element | 1 | htmlcs (H39.3.NoCaption warning) |

**Recommended action:** Verify whether the table on the 404 page is a data table or layout table. If it is a data table, add a `<caption>`.

---

## 5. Page-by-Page Results

### 5.1 Home Page (`/`)

**htmlcs:** 30 errors | 25 warnings | 101 notices
**axe:** 21 errors | 3 warnings | 0 notices

| WCAG SC | Level | Tool | Count | Description |
|---|---|---|---|---|
| 4.1.1 Parsing | A | htmlcs | 18 | Duplicate `id` attributes on heading elements |
| 1.1.1 Non-text Content | A | htmlcs/axe | 4/9 | Missing `alt` on images |
| 2.4.4 Link Purpose | A | htmlcs/axe | 6/6 | ORCID image links with no alt or link text |
| 4.1.2 Name, Role, Value | A | htmlcs | 1 | Chat `<textarea>` has no accessible name |
| 1.3.1 Info and Relationships | A | htmlcs | 1 | Chat form field not labeled |
| 1.4.1 Use of Color | A | axe | 4 | Links not distinguishable without color |
| 1.4.3 Contrast | AA | axe | 2 | TOC toggle button insufficient contrast |

---

### 5.2 Typical Chapter Pages (data-preparation, object-detection, ethics-of-ai, conclusions)

Each of these pages follows the same pattern:

**htmlcs:** 2 errors | 10 warnings | ~59–60 notices
**axe:** 0 errors | 3 warnings | 0 notices

| WCAG SC | Level | Tool | Count | Description |
|---|---|---|---|---|
| 4.1.2 Name, Role, Value | A | htmlcs | 1 | Chat `<textarea>` has no accessible name |
| 1.3.1 Info and Relationships | A | htmlcs | 1 | Chat form field not labeled |
| Landmark structure | Best practice | axe | 3 warnings | Nested/duplicate main landmark |

> The 2 errors on every chapter page are identical and come from the shared `base.html` chat widget.

---

### 5.3 Chapter: crop-mapping (Notebook-Heavy Page)

**htmlcs:** 672 errors | 190 warnings | 531 notices
**axe:** 635 errors | 3 warnings | 0 notices

This page renders a full Jupyter notebook via Quarto/nbconvert. The overwhelming majority of issues stem from the notebook HTML output, not the Django application shell.

| WCAG SC | Level | Tool | Count | Description |
|---|---|---|---|---|
| 2.4.4 Link Purpose | A | htmlcs/axe | 341/343 | Empty anchor elements (nbconvert line-number anchors) |
| 1.4.3 Contrast | AA | htmlcs/axe | 288/275 | Code syntax highlighting fails contrast ratio |
| 4.1.1 Parsing | A | htmlcs | 39 | Duplicate `id` attributes |
| 1.1.1 Non-text Content | A | htmlcs/axe | 2/2 | Images missing alt text (ORCID icons) |
| 4.1.2 / 1.3.1 | A | htmlcs | 1+1 | Chat textarea unlabeled |
| 1.4.1 Use of Color | A | axe | 14 | Links not distinguishable without color |
| Frame accessibility | Best practice | axe | 1 | `<iframe>` (embedded video) not fully testable |

---

### 5.4 404 Error Page (`/nonexistent-page/`)

**htmlcs:** 0 errors | 1 warning | 25 notices
**axe:** 0 errors | 0 warnings | 0 notices

The 404 page is effectively accessible. The one warning is an advisory for a table element lacking a caption (low severity).

---

## 6. Issues Not Detectable by Automated Testing

The following WCAG success criteria require manual human evaluation and were not assessed by automated tools:

| WCAG SC | Level | Description |
|---|---|---|
| 1.2.x | A/AA | All time-based media (audio, video): captions, audio descriptions, transcripts |
| 1.4.4 | AA | Text resize to 200% without loss of functionality — manual browser test required |
| 2.1.1 | A | Full keyboard navigation (tab order, focus trapping in chat widget) |
| 2.1.2 | A | No keyboard trap — chat modal must be closable via keyboard |
| 2.4.3 | A | Focus order that preserves meaning and operability |
| 2.4.7 | AA | Visible focus indicators on all interactive elements |
| 3.1.1 | A | Language of page — `<html lang="en">` should be verified |
| 3.3.1 | A | Error identification in chat form — if submission fails, error must be described |
| 3.3.2 | A | Labels or instructions for user inputs |
| 2.5.3 | A | Label in name — chat button visible label matches accessible name |

---

## 7. Prioritized Remediation Plan

Issues are ordered by severity and breadth of impact.

### Priority 1 — Critical (Affects Every Page, Level A)

**P1-A: Add `aria-label` to chat textarea** (`base.html`)
- Fixes: 1.3.1, 4.1.2 violations across all pages
- Effort: 1 line change

**P1-B: Add skip-to-main-content link** (`base.html`)
- Fixes: 2.4.1 advisory on all pages
- Effort: ~5 lines HTML + 2 lines CSS

**P1-C: Fix landmark structure** (`base.html`)
- Ensure exactly one `<main>` per page, not nested in other landmarks
- Fixes: axe landmark warnings across all pages
- Effort: Template refactor of layout structure

---

### Priority 2 — High (Home Page Content, Level A)

**P2-A: Add `alt` text to all images in notebook-rendered content**
- Author photos: `alt="[Name], Editor"`
- ORCID icons: `alt="ORCID profile for [Name]"` (or use `aria-label` on the `<a>`)
- Fix in the notebook/markdown source OR in the `convert_notebooks.py` post-processing step
- Fixes: 1.1.1 violations (9 images, 6 links)

**P2-B: Make links distinguishable without color**
- Add underline or other non-color indicator to body-text links
- Update `horizon.css` or `notebook.css`
- Fixes: 1.4.1 violations (4 on home, 14 on crop-mapping)

**P2-C: Fix duplicate `id` attributes**
- Audit heading IDs in content vs. TOC generation
- Ensure `chapter-toc.js` does not create elements with IDs already present in content
- Fixes: 4.1.1 violations (18 on home, 39 on crop-mapping)

---

### Priority 3 — High (Notebook Content Pipeline, Level A + AA)

**P3-A: Add `aria-hidden="true" tabindex="-1"` to empty nbconvert line-number anchors**
- Post-process HTML in `convert_notebooks.py` or `book_ingest.py`
- Fixes: 2.4.4 violations (341 empty anchors in crop-mapping alone)

**P3-B: Replace notebook syntax-highlight theme with WCAG-compliant colors**
- Override in `notebook.css`: ensure all code token colors meet 4.5:1 contrast against background
- Alternatively use a known-compliant theme (e.g., "a11y-dark" or "a11y-light")
- Fixes: 1.4.3 violations (288 htmlcs / 275 axe failures in crop-mapping)

---

### Priority 4 — Moderate (Warnings, Best Practices)

**P4-A: Verify and correct heading semantic structure**
- Confirm all visually-headed content uses `<h2>`–`<h6>` (not styled `<p>` or `<span>`)
- Fixes: H42 warnings

**P4-B: Verify contrast of transparent elements**
- Manually check elements with `rgba`/`opacity` near colored backgrounds
- Fixes: G18.Alpha warnings

**P4-C: Keyboard accessibility audit of chat widget**
- Verify chat FAB is reachable by Tab key
- Verify chat window can be closed with Escape
- Verify focus is managed when chat opens/closes
- Required for 2.1.1, 2.1.2 compliance

---

## 8. Appendix — Raw Issue Counts

### htmlcs Runner Results

| Page | Errors | Warnings | Notices | Total |
|---|---|---|---|---|
| home | 30 | 25 | 101 | 156 |
| chapter-data-preparation | 2 | 10 | 59 | 71 |
| chapter-crop-mapping | 672 | 190 | 531 | 1393 |
| chapter-object-detection | 2 | 10 | 60 | 72 |
| chapter-ethics-of-ai | 2 | 10 | 60 | 72 |
| chapter-conclusions | 2 | 10 | 59 | 71 |
| 404 | 0 | 1 | 25 | 26 |
| **TOTAL** | **710** | **256** | **895** | **1861** |

### axe Runner Results

| Page | Errors | Warnings | Notices | Total |
|---|---|---|---|---|
| home | 21 | 3 | 0 | 24 |
| chapter-data-preparation | 0 | 3 | 0 | 3 |
| chapter-crop-mapping | 635 | 3 | 0 | 638 |
| chapter-object-detection | 0 | 3 | 0 | 3 |
| chapter-ethics-of-ai | 0 | 3 | 0 | 3 |
| chapter-conclusions | 0 | 3 | 0 | 3 |
| 404 | 0 | 0 | 0 | 0 |
| **TOTAL** | **656** | **18** | **0** | **674** |

### Unique Error Codes — htmlcs

| Code | WCAG SC | Level | Description | Pages Affected |
|---|---|---|---|---|
| F77 | 4.1.1 | A | Duplicate `id` attribute | home, crop-mapping |
| H37 | 1.1.1 | A | `<img>` missing `alt` | home |
| H30.2 | 1.1.1 | A | Image-only link missing alt | home, crop-mapping |
| H91.Textarea.Name | 4.1.2 | A | Textarea has no accessible name | all |
| F68 | 1.3.1 | A | Form field not labeled | all |
| H91.A.NoContent | 2.4.4 | A | Anchor with href but no content | crop-mapping |
| G18.Fail | 1.4.3 | AA | Insufficient contrast | crop-mapping |
| G18.Alpha | 1.4.3 | AA | Transparency — contrast unverifiable | all (warning) |
| H42 | 1.3.1 | A | Possible heading not marked up | home, chapters (warning) |
| H48 | 1.3.1 | A | Navigation not marked as list | home, chapters (warning) |
| C32 | 1.4.10 | AA | Fixed/wide content may require 2D scroll | all (warning) |
| F24.FGColour | 1.4.3 | AA | Inline foreground color without background | home (warning) |

### Unique Error Codes — axe

| Code | WCAG SC | Level | Description | Pages Affected |
|---|---|---|---|---|
| image-alt | 1.1.1 | A | Images missing alternative text | home, crop-mapping |
| link-name | 2.4.4 / 4.1.2 | A | Links with no discernible text | home, crop-mapping |
| link-in-text-block | 1.4.1 | A | Links not distinguishable without color | home, crop-mapping |
| color-contrast | 1.4.3 | AA | Insufficient contrast ratio | home, crop-mapping |
| frame-tested | Best practice | — | `<iframe>` could not be tested | crop-mapping |
| landmark-main-is-top-level | Best practice | — | `<main>` nested inside another landmark | all (warning) |
| landmark-no-duplicate-main | Best practice | — | Multiple `<main>` landmarks | all (warning) |
| landmark-unique | Best practice | — | Identical landmark roles with no label | all (warning) |

---

## 9. Section 508 Conformance Mapping

| Section 508 Provision | WCAG SC | Status | Notes |
|---|---|---|---|
| §1194.22(a) Text equivalents | 1.1.1 | **FAIL** | Author photos + ORCID icons missing alt text |
| §1194.22(b) Multimedia equivalents | 1.2.x | Untested | No automated test possible |
| §1194.22(c) Color not sole means | 1.4.1 | **FAIL** | Links rely on color only |
| §1194.22(d) Documents readable without stylesheet | 2.4.4 | **FAIL** | 341 empty anchor elements in notebook |
| §1194.22(i) Frames titled | 4.1.2 | **FAIL** (warning) | `<iframe>` not fully testable by axe |
| §1194.22(n) Form accessibility | 1.3.1, 4.1.2 | **FAIL** | Chat textarea has no label |
| §1194.22(o) Skip navigation | 2.4.1 | **FAIL** (likely) | No skip link observed |
| §1194.21(d) Information for assistive tech | 4.1.2 | **FAIL** | Duplicate IDs, unlabeled elements |
| §1194.21(j) Contrast / visual presentation | 1.4.3 | **FAIL** | Notebook code fails contrast ratio |

---

*Report generated by automated pa11y testing. Automated testing identifies a subset of accessibility issues; full compliance assessment also requires manual testing with assistive technologies (NVDA, JAWS, VoiceOver) and keyboard-only navigation.*
