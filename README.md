# EarthRISE Applied AI & Deep Learning Book — Django Site

[![Python: 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![EarthRISE: Development](https://img.shields.io/badge/EarthRISE-Development-b50000?labelColor=191f4c)](https://appliedsciences.nasa.gov/what-we-do/capacity-building/develop)

A Django web application that serves the
[NASA EarthRISE Applied Artificial Intelligence and Deep Learning Book](https://nasa-earthrise.github.io/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book/)
as a styled, navigable website.

Content is sourced from the companion book repository (Quarto project) and
rendered into a local SQLite database. No live internet connection to the book
repo is required at serve time.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project layout](#project-layout)
3. [First-time setup](#first-time-setup)
4. [Updating content when the book repo changes](#updating-content-when-the-book-repo-changes)
   - [How content flows from source to site](#how-content-flows-from-source-to-site)
   - [Step 1 — Pull the latest source repo changes](#step-1--pull-the-latest-source-repo-changes)
   - [Step 2 — Fetch the gh-pages branch](#step-2--fetch-the-gh-pages-branch)
   - [Step 3 — Re-render chapter HTML](#step-3--re-render-chapter-html)
   - [Adding a new chapter or part](#adding-a-new-chapter-or-part)
   - [Removing or renaming a chapter](#removing-or-renaming-a-chapter)
   - [Changing a chapter's part assignment or order](#changing-a-chapters-part-assignment-or-order)
5. [Management commands reference](#management-commands-reference)
6. [Running the development server](#running-the-development-server)
7. [Architecture overview](#architecture-overview)
8. [Design system](#design-system)

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.9+ | Tested with the `earthrise-applied-artificial-intelligence-and-deep-learning-book-django` conda environment |
| Git | Required by `convert_notebooks` to read the gh-pages branch |
| The book source repo | Must be cloned as a sibling directory (see below) |

**Python packages** (install into your environment):

```
Django
nbformat
nbconvert
beautifulsoup4
pyyaml
markdown
```

---

## Project layout

```
websites/
├── EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book/   ← book source repo
│   ├── .git/                     (contains the gh-pages branch)
│   ├── _quarto.yml
│   ├── index.md                  (introduction)
│   ├── 02_Data_Preparation/
│   ├── 03_Semantic_Segmentation/
│   └── ...
│
└── EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book-django/   ← this repo
    ├── manage.py
    ├── db.sqlite3                 (SQLite database — stores rendered HTML)
    ├── webapp/
    │   ├── models.py              (Part, Chapter)
    │   ├── views.py
    │   ├── context_processors.py  (sidebar navigation)
    │   └── management/commands/
    │       ├── populate_chapters.py   (create/update Part & Chapter records)
    │       └── convert_notebooks.py   (render source files → html_content)
    ├── templates/
    │   ├── base.html
    │   ├── home.html              (introduction page)
    │   └── chapter.html
    └── static/
        ├── css/
        └── js/
```

`NOTEBOOK_SOURCE_DIR` in `settings.py` points to the sibling source repo:

```python
NOTEBOOK_SOURCE_DIR = BASE_DIR.parent / "EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book"
```

---

## First-time setup

```bash
# 1. Clone both repos into the same parent directory
git clone https://github.com/NASA-EarthRISE/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book.git
git clone <this-repo-url>

# 2. Activate your Python environment
conda activate earthrise-applied-artificial-intelligence-and-deep-learning-book-django

# 3. Apply migrations
python manage.py migrate

# 4. Create Part and Chapter records
python manage.py populate_chapters

# 5. Fetch gh-pages and render HTML into the database
cd ../EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book
git fetch origin
cd ../EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book-django
python manage.py convert_notebooks

# 6. Start the dev server
python manage.py runserver
```

---

## Updating content when the book repo changes

### How content flows from source to site

Understanding the pipeline makes each update step make sense:

```
Book source repo (GitHub)
    │
    ├─ main/default branch  ──→  .ipynb / .md source files
    │                             (used only as fallback if gh-pages HTML is missing)
    │
    └─ gh-pages branch  ──────→  Pre-rendered Quarto HTML
                                  (primary source — contains polished headings,
                                   callouts, code cells, figures, and author blocks)
                                      │
                                      ▼
                              convert_notebooks.py
                                  - git show remotes/origin/gh-pages:<path>
                                  - Extracts #quarto-document-content
                                  - Strips navigation chrome, scripts, styles
                                  - Fixes relative asset URLs
                                  - Promotes heading anchors
                                  - Stores clean HTML fragment in db.sqlite3
                                      │
                                      ▼
                              Chapter.html_content  (SQLite)
                                      │
                                      ▼
                              chapter.html / home.html template
                                  - Renders the stored fragment verbatim
```

The key point: **the site reads from `remotes/origin/gh-pages` inside the source
repo's local `.git` store, not from the working tree.** This means you must run
`git fetch origin` in the source repo whenever you want to pick up upstream
changes — a `git pull` on the default branch alone is not enough.

---

### Step 1 — Pull the latest source repo changes

```bash
cd path/to/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book

# Update both the default branch and all remote refs (including gh-pages)
git pull
git fetch origin
```

`git fetch origin` downloads the latest `remotes/origin/gh-pages` ref, which is
what `convert_notebooks` reads. You do not need to check out or merge gh-pages
locally.

To confirm the gh-pages branch is available:

```bash
git branch -r | grep gh-pages
# Should print:  remotes/origin/gh-pages
```

---

### Step 2 — Fetch the gh-pages branch

This is already covered by `git fetch origin` above. If you ever need to
verify which chapters have fresh gh-pages HTML:

```bash
# List all HTML files on the gh-pages branch
git ls-tree -r --name-only remotes/origin/gh-pages | grep "\.html$"
```

Each `.html` file corresponds to a chapter. The path structure mirrors the
source repo (e.g. `03_Semantic_Segmentation/01__Crop_Mapping/notebooks/Rice_Mapping_Bhutan_2021.html`).

---

### Step 3 — Re-render chapter HTML

After fetching, re-run `convert_notebooks` from the **Django project directory**:

```bash
cd path/to/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book-django

# Re-render all chapters
python manage.py convert_notebooks
```

Expected output:

```
  [gh-pages]  Introduction
  [gh-pages]  1. Data Preparation
  [gh-pages]  2. Crop Mapping
  ...
Done. 14 converted (14 gh-pages, 0 nbconvert), 0 errors.
```

**To update only one chapter** (faster for small changes):

```bash
python manage.py convert_notebooks --slug crop-mapping
python manage.py convert_notebooks --slug introduction
```

**If a chapter's gh-pages HTML is missing** (not yet published), the command
automatically falls back to rendering the raw `.ipynb` or `.md` source file
with `nbconvert`/`markdown`. You can force this path for all chapters with:

```bash
python manage.py convert_notebooks --force-nbconvert
```

After running `convert_notebooks`, **no server restart is needed** — the
updated HTML is read from the database on the next page request.

---

### Adding a new chapter or part

New chapters and parts are defined in one place:
`webapp/management/commands/populate_chapters.py`.

**1. Add the entry to `CHAPTERS` (and `PARTS` if needed):**

```python
# In PARTS (if this chapter belongs to a new part):
{'title': 'New Part Title', 'slug': 'new-part-slug', 'order': 4},

# In CHAPTERS:
{
    'order': 12,                        # Float — controls sidebar/prev-next order
    'title': 'My New Chapter',
    'slug': 'my-new-chapter',           # URL slug: /chapter/my-new-chapter/
    'content_type': 'notebook',         # 'notebook' or 'markdown'
    'source_path': '13_NewChapter/index.ipynb',  # Relative to NOTEBOOK_SOURCE_DIR
    'notebook_filename': 'index.ipynb', # Bare filename (used in JupyterLite links)
    'part_slug': 'new-part-slug',       # None if not in a part
    'is_intro': False,
},
```

`source_path` must match the path to the file **in the source repo's working
tree**. `convert_notebooks` derives the gh-pages HTML path from this by
replacing the `.ipynb`/`.qmd`/`.md` extension with `.html`.

**2. Run `populate_chapters` to create the database record:**

```bash
python manage.py populate_chapters
```

This command is idempotent — it uses `update_or_create` keyed on `slug`, so
running it again on existing chapters updates their metadata without
overwriting `html_content`.

**3. Fetch the latest gh-pages and render the new chapter:**

```bash
cd path/to/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book
git fetch origin
cd path/to/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book-django
python manage.py convert_notebooks --slug my-new-chapter
```

---

### Removing or renaming a chapter

`populate_chapters` only creates or updates records — it never deletes. To
remove a chapter:

```bash
# Option A: Django admin UI
# Navigate to /admin/webapp/chapter/ and delete the record there.

# Option B: Django shell
python manage.py shell -c "from webapp.models import Chapter; Chapter.objects.get(slug='old-slug').delete()"
```

To rename a chapter (title change only, same slug):

1. Update `title` in `CHAPTERS` inside `populate_chapters.py`
2. Run `python manage.py populate_chapters`

To change a chapter's slug (this changes its URL):

1. Update both `slug` and any references in `CHAPTERS`
2. Run `python manage.py populate_chapters` — this creates a **new** record
   with the new slug (the old one is not deleted automatically)
3. Delete the old record via the admin or shell as shown above

---

### Changing a chapter's part assignment or order

Edit the `part_slug` or `order` field in `populate_chapters.py`, then:

```bash
python manage.py populate_chapters
```

`order` is a float, which allows sub-chapter ordering (e.g. `2.1`, `2.2`,
`2.3` for chapters inside a part). The sidebar and prev/next navigation are
both driven by this field.

---

## Management commands reference

### `populate_chapters`

```
python manage.py populate_chapters
```

Creates or updates `Part` and `Chapter` database records from the hardcoded
lists in `populate_chapters.py`. Safe to run multiple times. Does **not**
overwrite `html_content`.

Use when: adding, renaming, or reordering chapters/parts.

---

### `convert_notebooks`

```
python manage.py convert_notebooks [--slug SLUG] [--force-nbconvert]
```

| Flag | Description |
|---|---|
| _(no flags)_ | Convert all chapters |
| `--slug <slug>` | Convert only the chapter with this slug |
| `--force-nbconvert` | Skip gh-pages HTML; render from raw `.ipynb`/`.md` for all chapters |

Reads Quarto-rendered HTML from `remotes/origin/gh-pages` in the source repo
(primary path), or renders raw source files with `nbconvert`/`markdown`
(fallback). Stores the result in `Chapter.html_content`.

Use when: the book repo has been updated and you want the site to reflect
the new content.

---

## Running the development server

```bash
python manage.py runserver
```

The site is served at `http://127.0.0.1:8000/`.

The Django admin is at `http://127.0.0.1:8000/admin/` (create a superuser
with `python manage.py createsuperuser` if needed).

---

## Architecture overview

```
Request
  │
  ▼
urls.py  ──  /                     →  views.home    →  home.html
          ──  /chapter/<slug>/     →  views.chapter →  chapter.html
          ──  /admin/              →  Django admin
  │
  ▼
context_processors.navigation()
  - Builds sidebar nav_items list (parts + standalone chapters, ordered)
  - Injected into every template context automatically
  │
  ▼
Templates (base.html → home.html / chapter.html)
  - Renders Chapter.html_content verbatim (|safe filter)
  - chapter-toc.js builds right-side "Table of contents" from h1/h2/h3 headings
  - sidebar.js handles mobile nav toggle
```

**Models:**

- `Part` — a thematic group of chapters (title, slug, order)
- `Chapter` — a single page (title, slug, order, source_path, html_content,
  is_intro, part FK)

**Database:** SQLite (`db.sqlite3`). The 49 MB file is dominated by
`html_content` storing the pre-rendered HTML for all 14 chapters.

---

## Design system

The site uses the **NASA Horizon Design System** (`static/css/horizon.css`).
Key CSS custom properties are defined in `:root` and control colors, fonts,
spacing, and border radii throughout.

Chapter-specific styles (Quarto HTML compatibility, notebook output formatting,
code folding, right-side TOC layout) live in `static/css/notebook.css`.

The right-side table of contents (`chapter-toc.js`) supports two modes:

- **depth-2** — flat list of h1 + h2 headings (not currently used)
- **depth-3** — h1 + h2 + h3, with h3 entries grouped under their parent h2
  in a collapsible accordion; scroll-spy highlights the active heading as
  the user reads

Both `home.html` and `chapter.html` use depth-3.


## License and Distribution

EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book is distributed by EarthRISE under the terms of the MIT License. See
[LICENSE](https://github.com/NASA-EarthRISE/earthrise-toolkit_EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book/blob/main/LICENSE) in this directory for more information.