"""
Management command: convert_notebooks

Primary path: reads pre-rendered Quarto HTML from the source repo's
  remotes/origin/gh-pages branch, extracts #quarto-document-content, and
  stores clean chapter HTML ready for the Horizon-styled Django template.

Fallback path: for chapters with no gh-pages HTML (markdown-only chapters or
  future additions not yet published), falls back to the nbconvert pipeline.

Quarto HTML cleanup performed:
  - Strip duplicate <h1> title (Django chapter template owns the title)
  - Strip all navigation chrome (sidebar, breadcrumbs, nav-footer, TOC links)
  - Strip all <script> blocks
  - Strip all Quarto/Bootstrap <link>/<style> blocks except the Pandoc
    code-highlight <style> block (which is inlined into notebook.css anyway)
  - Keep: quarto-title-meta-author (author grid), callouts, code-fold details,
    video iframes, section headings, all body content
"""
import os
import re
import subprocess

import markdown as md_lib
import nbformat
import yaml
from bs4 import BeautifulSoup, Comment
from django.conf import settings
from django.core.management.base import BaseCommand
from nbconvert import HTMLExporter

from webapp.models import Chapter
from webapp.book_ingest import chunk_chapter
from webapp.rag import get_store


class Command(BaseCommand):
    help = 'Convert chapter source files to HTML and store in Chapter.html_content.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            default=None,
            help='Only convert the chapter with this slug.',
        )
        parser.add_argument(
            '--force-nbconvert',
            action='store_true',
            default=False,
            help='Skip gh-pages HTML and always use the nbconvert pipeline.',
        )
        parser.add_argument(
            '--no-embed',
            action='store_true',
            default=False,
            help='Skip embedding into the vector store after conversion.',
        )

    def handle(self, *args, **options):
        source_dir = settings.NOTEBOOK_SOURCE_DIR

        qs = Chapter.objects.all()
        if options['slug']:
            qs = qs.filter(slug=options['slug'])

        # nbconvert exporter kept as fallback
        exporter = HTMLExporter()
        exporter.template_name = 'basic'

        converted = 0
        errors = 0
        used_ghpages = 0
        used_nbconvert = 0

        for chapter in qs:
            if not chapter.source_path:
                self.stdout.write(f'  Skipping (no source_path): {chapter.title}')
                continue

            source_file = os.path.join(source_dir, chapter.source_path)

            try:
                html = None

                if not options['force_nbconvert']:
                    html = self._try_ghpages(chapter.source_path, source_dir)
                    if html is not None:
                        used_ghpages += 1
                        self.stdout.write(f'  [gh-pages]  {chapter.title}')

                if html is None:
                    if not os.path.exists(source_file):
                        self.stderr.write(
                            self.style.WARNING(f'  Source not found: {source_file}')
                        )
                        errors += 1
                        continue
                    if chapter.content_type == 'notebook':
                        html = self._convert_notebook_fallback(source_file, exporter)
                    else:
                        html = self._convert_markdown(source_file)
                    used_nbconvert += 1
                    self.stdout.write(f'  [nbconvert] {chapter.title}')

                chapter.html_content = html
                chapter.save(update_fields=['html_content'])
                converted += 1

                # ── Embed into vector store ───────────────────────────────
                if not options['no_embed']:
                    try:
                        store = get_store()
                        store.delete_chapter_docs(chapter.slug)
                        docs = chunk_chapter(chapter.slug, chapter.title, html)
                        store.upsert(docs)
                        self.stdout.write(f'    → embedded {len(docs)} chunks')
                    except Exception as emb_exc:
                        self.stderr.write(
                            self.style.WARNING(f'    WARNING embed failed for {chapter.slug}: {emb_exc}')
                        )

            except Exception as exc:
                import traceback
                self.stderr.write(self.style.ERROR(f'  ERROR {chapter.title}: {exc}'))
                self.stderr.write(traceback.format_exc())
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. {converted} converted '
            f'({used_ghpages} gh-pages, {used_nbconvert} nbconvert), {errors} errors.'
        ))

    # ------------------------------------------------------------------
    # Primary path – gh-pages Quarto HTML
    # ------------------------------------------------------------------

    def _try_ghpages(self, source_path, repo_dir):
        """
        Read the Quarto-rendered HTML for this chapter from the remote
        gh-pages branch using `git show`, clean it up, and return the
        content fragment.  Returns None if the file doesn't exist there.
        """
        # Derive the gh-pages HTML path from the notebook/markdown source path
        html_rel = re.sub(r'\.(ipynb|qmd|md)$', '.html', source_path.replace('\\', '/'))
        git_ref = f'remotes/origin/gh-pages:{html_rel}'

        try:
            result = subprocess.run(
                ['git', 'show', git_ref],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        if result.returncode != 0:
            return None

        return self._clean_quarto_html(result.stdout)

    def _clean_quarto_html(self, raw_html):
        """
        Extract #quarto-document-content from the full Quarto page, strip
        all navigation chrome, and return the clean fragment.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')

        # ── 1. Find the document content div ─────────────────────────────
        content = soup.find(id='quarto-document-content')
        if not content:
            # Older Quarto may use a different wrapper; try <main>
            content = soup.find('main') or soup.find(id='content')
        if not content:
            return None  # Unrecognised structure → fall back to nbconvert

        # ── 1a. Neutralise landmark semantics on the root element ─────────
        # If Quarto used <main> as the content wrapper, inserting it inside
        # Django's own <main> creates a duplicate main landmark (WCAG 4.1.2).
        # Change to <div> so the page has exactly one <main>.
        if content.name == 'main':
            content.name = 'div'

        # ── 1b. Neutralise the title-block <header> landmark ─────────────
        # <header id="title-block-header"> inside <main> creates a nested
        # header landmark that axe flags.  Convert to <div>.
        title_block_header = content.find('header', id='title-block-header')
        if title_block_header:
            title_block_header.name = 'div'
        # Also convert any remaining <header>/<footer> inside content that
        # would create unexpected landmark regions.
        for tag_name in ('header', 'footer'):
            for el in content.find_all(tag_name):
                el.name = 'div'

        # ── 2. Remove duplicate chapter title ────────────────────────────
        # Django's chapter.html template already displays the chapter title.
        title_div = content.find('div', class_='quarto-title')
        if title_div:
            title_div.decompose()

        # Remove empty quarto-title-meta (date / license – less important)
        title_meta = content.find('div', class_='quarto-title-meta')
        if title_meta:
            title_meta.decompose()

        # ── 3. Remove navigation chrome inside the content area ───────────
        nav_selectors = [
            ('nav', {}),                              # any <nav>
            ('div', {'id': 'quarto-navigation-tool'}),
            ('div', {'class': 'page-navigation'}),   # prev/next at bottom
            ('div', {'class': 'quarto-secondary-nav'}),
            ('div', {'id': 'quarto-margin-sidebar'}),
            ('div', {'class': 'toc-actions'}),
            ('nav', {'id': 'TOC'}),
            ('div', {'class': 'quarto-page-breadcrumbs'}),
        ]
        for tag, attrs in nav_selectors:
            for el in content.find_all(tag, attrs):
                el.decompose()

        # ── 4. Remove HTML comments ───────────────────────────────────────
        for comment in content.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # ── 5. Strip all <script> and stray <style>/<link> elements ──────
        for tag in content.find_all(['script', 'link']):
            tag.decompose()
        # Keep no <style> blocks inside content either
        for tag in content.find_all('style'):
            tag.decompose()

        # ── 6. Fix relative asset URLs that would break outside the repo ─
        # (Images embedded as data URIs in ORCID badges are already inline.)
        # External absolute URLs (https://) are fine; relative ones need the
        # gh-pages base prepended.
        BASE = 'https://nasa-earthrise.github.io/EarthRISE-Applied-Artificial-Intelligence-and-Deep-Learning-Book/'
        for tag in content.find_all(True):
            for attr in ('src', 'href', 'data-src'):
                val = tag.get(attr, '')
                if val and not val.startswith(('http', 'data:', '#', 'mailto:')):
                    # Resolve relative path against BASE
                    tag[attr] = BASE + val.lstrip('/')

        # ── 7. Promote data-anchor-id → id on headings ───────────────────
        # Quarto's JS normally does this; without it anchors don't resolve.
        # For h1 elements with no data-anchor-id, generate a slug from text.
        for heading in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if heading.get('id'):
                continue
            anchor = heading.get('data-anchor-id')
            if anchor:
                heading['id'] = anchor
            elif heading.name == 'h1':
                # Generate a Quarto-style slug: lowercase, spaces → hyphens,
                # strip non-alphanumeric except hyphens.
                text = heading.get_text()
                slug = re.sub(r'[^\w\s-]', '', text.lower())
                slug = re.sub(r'[\s_]+', '-', slug).strip('-')
                if slug:
                    heading['id'] = slug

        # ── 7a. Remove duplicate IDs (section vs heading) ────────────────
        # Quarto wraps every section in <section id="same-id"> AND puts the
        # same id on the heading inside.  Remove it from the <section> so
        # each id appears only once on the page (WCAG 4.1.1 / F77).
        for section in content.find_all('section'):
            section_id = section.get('id')
            if not section_id:
                continue
            # If a child heading already carries this id, drop it from the section
            duplicate_heading = section.find(
                ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], id=section_id
            )
            if duplicate_heading:
                del section['id']

        # ── 8. Fix YouTube iframes ─────────────────────────────────────────
        # Switch to privacy-enhanced mode, add referrerpolicy, fill title.
        for iframe in content.find_all('iframe'):
            src = iframe.get('src', '')
            # Switch youtube.com/embed → youtube-nocookie.com/embed
            if 'youtube.com/embed' in src:
                iframe['src'] = src.replace('youtube.com/embed', 'youtube-nocookie.com/embed')
            # Ensure referrerpolicy is set for cross-origin embeds
            if 'youtube' in iframe.get('src', ''):
                iframe['referrerpolicy'] = 'strict-origin-when-cross-origin'
                # Extend allow attribute with web-share if not already present
                allow = iframe.get('allow', '')
                if 'web-share' not in allow:
                    iframe['allow'] = (allow + '; web-share').lstrip('; ')
            # All iframes must have a title for screen readers (WCAG 4.1.2)
            if not iframe.get('title', '').strip():
                iframe['title'] = 'Embedded video'

        # ── 9. Fix empty anchor elements (line-number anchors from nbconvert)
        # Quarto/nbconvert generates <a href="#cb1-1"></a> for code line numbers.
        # These have no text content and confuse screen readers (WCAG 2.4.4).
        # Mark them as aria-hidden and remove from tab order.
        for a in content.find_all('a', href=True):
            if not a.get_text(strip=True) and not a.find('img'):
                a['aria-hidden'] = 'true'
                a['tabindex'] = '-1'

        # ── 10. Fix images missing alt text ──────────────────────────────
        # Author photos and ORCID icons in Quarto-generated HTML lack alt.
        _author_alts = {
            'Tim_img':    'Tim Dye',
            'Biplov_img': 'Biplov Bhandari',
            'David_img':  'David Lagomasino',
            'Lena_river': 'Lena River delta',
        }
        for img in content.find_all('img'):
            # Skip images that already have an alt attribute (even empty "")
            if img.get('alt') is not None:
                continue
            src = img.get('src', '')
            # ORCID badge icons — either URL-based or base64 data URIs
            # (Quarto embeds them inline as data:image/png; parent <a> has
            #  class="quarto-title-author-orcid" or href matching orcid.org)
            parent_a = img.find_parent('a')
            parent_href = parent_a.get('href', '') if parent_a else ''
            parent_class = ' '.join(parent_a.get('class', [])) if parent_a else ''
            is_orcid_icon = (
                ('orcid.org' in src and 'orcid_16x16' in src)
                or 'quarto-title-author-orcid' in parent_class
                or 'orcid.org/0000' in parent_href
            )
            if is_orcid_icon:
                img['alt'] = 'ORCID iD'
            # Book cover
            elif 'Book_Cover' in src:
                img['alt'] = 'Applied Artificial Intelligence and Deep Learning Book cover'
            else:
                # Named author/asset images
                matched = False
                for key, name in _author_alts.items():
                    if key in src:
                        img['alt'] = f'Photo of {name}'
                        matched = True
                        break
                if not matched:
                    # Treat remaining unlabelled inline images as decorative
                    img['alt'] = ''

        # ── 11. Fix ORCID links that contain only an image (no text) ──────
        # The image-only link has no accessible name unless the img has alt.
        # The above step (10) gives the img alt="ORCID iD"; also add
        # aria-label to the link itself for screen readers that read links
        # by link text rather than img alt (WCAG 2.4.4 / 4.1.2).
        for a in content.find_all('a', href=True):
            href = a.get('href', '')
            if 'orcid.org/0000' not in href:
                continue
            # Only patch links that have no text content (image-only links)
            if not a.get_text(strip=True) and not a.get('aria-label'):
                a['aria-label'] = 'ORCID author profile (opens in new tab)'

        # ── 12. Make scrollable code blocks keyboard-accessible ───────────
        # WCAG 2.1 SC 2.1.1: scrollable content must be keyboard reachable.
        # <pre> elements in Quarto code blocks have overflow-x:auto (from
        # the div.sourceCode container) and can overflow horizontally.
        # Adding tabindex="0" lets keyboard users focus and scroll them.
        for pre in content.find_all('pre'):
            if pre.get('tabindex') is None:
                pre['tabindex'] = '0'

        return str(content)

    # ------------------------------------------------------------------
    # Fallback path – nbconvert pipeline (original implementation)
    # ------------------------------------------------------------------

    def _convert_notebook_fallback(self, path, exporter):
        with open(path, encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)

        author_html = self._build_author_block(nb)
        nb.cells = [cell for cell in nb.cells if cell.cell_type != 'raw']

        body, _ = exporter.from_notebook_node(nb)
        body = self._extract_body_content(body)
        body = self._strip_embedded_assets(body)
        body = self._process_quarto_syntax(body)
        body = self._apply_code_folding(body)

        if author_html:
            body = author_html + '\n' + body
        return body

    # ── Fallback helpers (unchanged from previous version) ───────────────

    ORCID_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        'width="14" height="14" style="vertical-align:middle;margin-right:3px" aria-hidden="true">'
        '<path d="M128 0C57.3 0 0 57.3 0 128s57.3 128 128 128 128-57.3 128-128S198.7 0 128 0z" fill="#a6ce39"/>'
        '<path d="M86.3 186.2H70.9V79.1h15.4v107.1zm-7.7-119.8c-5.1 0-9.2-4.1-9.2-9.2s4.1-9.2 9.2-9.2 '
        '9.2 4.1 9.2 9.2-4.1 9.2-9.2 9.2zm107.2 119.8h-15.4v-52c0-12.4-.2-28.3-17.2-28.3-17.3 0-19.9 '
        '13.5-19.9 27.4v52.9H117.9V108.8h14.8v14.6h.2c2.1-3.9 7.1-8 14.6-8 15.6 0 18.5 10.3 18.5 '
        '23.6v47.2z" fill="#fff"/>'
        '</svg>'
    )

    def _build_author_block(self, nb):
        raw_cells = [c for c in nb.cells if c.cell_type == 'raw']
        if not raw_cells:
            return ''
        yaml_text = re.sub(r'^---\s*\n?', '', raw_cells[0].source)
        yaml_text = re.sub(r'\n?---\s*$', '', yaml_text)
        try:
            meta = yaml.safe_load(yaml_text)
        except Exception:
            return ''
        authors = meta.get('author', [])
        if not authors:
            return ''
        parts = ['<div class="chapter-authors">']
        for author in authors:
            name = author.get('name', '')
            orcid = author.get('orcid', '')
            aff_names = [a.get('name', '') for a in author.get('affiliations', [])
                         if isinstance(a, dict) and a.get('name')]
            parts.append('<div class="chapter-author">')
            parts.append(f'<span class="chapter-author__name">{name}</span>')
            if orcid:
                parts.append(
                    f'<a class="chapter-author__orcid" href="https://orcid.org/{orcid}" '
                    f'target="_blank" rel="noopener noreferrer">'
                    f'{self.ORCID_SVG}{orcid}</a>'
                )
            if aff_names:
                parts.append(f'<span class="chapter-author__affil">{" &middot; ".join(aff_names)}</span>')
            parts.append('</div>')
        parts.append('</div>')
        return '\n'.join(parts)

    def _extract_body_content(self, html):
        m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return html

    def _strip_embedded_assets(self, html):
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        return html

    def _process_quarto_syntax(self, html):
        def _replace_video(m):
            url = m.group(1).strip().replace('watch?v=', 'embed/')
            return (
                '<div class="quarto-video ratio ratio-16x9">'
                f'<iframe src="{url}" frameborder="0" '
                'allowfullscreen loading="lazy" title="Embedded video"></iframe>'
                '</div>'
            )
        html = re.sub(
            r'\{\{&lt;\s*video\s+(?:<a[^>]*>)?([^\s<&]+)(?:</a>)?\s*&gt;\}\}',
            _replace_video, html)
        html = re.sub(r'\{\{<\s*video\s+([^\s>]+)\s*>\}\}', _replace_video, html)
        html = re.sub(r'<p>\s*:::\s*\{\.content-visible[^}]*\}[^<]*</p>', '', html)
        html = re.sub(r':::\s*\{\.content-visible[^}]*\}\s*\n?', '', html)

        def _replace_callout(m):
            ctype = m.group(1) or 'note'
            inner = re.sub(r'^(.*?)</p>', r'\1', m.group(2).strip(), count=1)
            label = {'note': 'Note', 'warning': 'Warning', 'tip': 'Tip',
                     'important': 'Important', 'caution': 'Caution'}.get(ctype, ctype.title())
            return (
                f'<div class="callout callout-style-simple callout-{ctype} no-icon">'
                f'<div class="callout-body d-flex">'
                f'<div class="callout-body-container"><p><strong>{label}</strong></p>{inner}</div>'
                f'</div></div>'
            )
        html = re.compile(
            r'<p>\s*:::\s*\{\.callout-(\w+)[^}]*\}\s*\n?(.*?)'
            r'\s*(?::::\s*</p>|</p>\s*(?:<p>\s*:::\s*</p>)+)',
            re.DOTALL,
        ).sub(_replace_callout, html)
        html = re.sub(r'<p>\s*:::\s*</p>', '', html)
        html = re.sub(r':::\s*\{[^}]*\}', '', html)
        html = re.sub(r':::', '', html)
        html = re.sub(r'<p>\s*(<div class="quarto-video[^"]*">.*?</div>)\s*</p>',
                      r'\1', html, flags=re.DOTALL)
        return html

    def _apply_code_folding(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        for code_cell in soup.find_all('div', class_='jp-CodeCell'):
            input_wrapper = code_cell.find('div', class_='jp-Cell-inputWrapper')
            if input_wrapper:
                details = soup.new_tag('details', attrs={'class': 'code-fold', 'open': ''})
                summary = soup.new_tag('summary')
                summary.string = 'Show code'
                details.append(summary)
                input_wrapper.replace_with(details)
                details.append(input_wrapper)
            output_wrapper = code_cell.find('div', class_='jp-Cell-outputWrapper')
            if output_wrapper and output_wrapper.get_text(strip=True):
                details = soup.new_tag('details', attrs={'class': 'output-fold'})
                summary = soup.new_tag('summary')
                summary.string = 'Show output'
                details.append(summary)
                output_wrapper.replace_with(details)
                details.append(output_wrapper)
        return str(soup)

    # ------------------------------------------------------------------
    # Markdown file conversion
    # ------------------------------------------------------------------

    def _convert_markdown(self, path):
        with open(path, encoding='utf-8') as f:
            text = f.read()
        text = re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=re.DOTALL)
        text = re.sub(r'\{[^}]*\}', '', text)
        return md_lib.markdown(
            text,
            extensions=['fenced_code', 'tables', 'attr_list', 'toc'],
        )
