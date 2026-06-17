from django.db import models
from django.urls import reverse


class Part(models.Model):
    """A thematic grouping of chapters (e.g. 'Semantic Segmentation')."""
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Chapter(models.Model):
    """A single chapter — either a Jupyter notebook or a Markdown file."""

    CONTENT_TYPE_CHOICES = [
        ('notebook', 'Jupyter Notebook'),
        ('markdown', 'Markdown'),
    ]

    part = models.ForeignKey(
        Part,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapters',
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, max_length=200)
    # order uses float so sub-chapters can be 3.1, 3.2, etc.
    order = models.FloatField(default=0)
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='notebook',
    )
    # Path to source file relative to NOTEBOOK_SOURCE_DIR
    source_path = models.CharField(max_length=500, blank=True)
    # Bare filename used in JupyterLite URL query param (e.g. Rice_Mapping_Bhutan_2021.ipynb)
    notebook_filename = models.CharField(max_length=300, blank=True)
    # Pre-rendered HTML from nbconvert / markdown package
    html_content = models.TextField(blank=True)
    # True for the introduction / index page
    is_intro = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.is_intro:
            return reverse('webapp:home')
        return reverse('webapp:chapter', kwargs={'slug': self.slug})

    @property
    def prev_chapter(self):
        return (
            Chapter.objects.filter(order__lt=self.order)
            .exclude(is_intro=True)
            .order_by('-order')
            .first()
        )

    @property
    def next_chapter(self):
        return (
            Chapter.objects.filter(order__gt=self.order)
            .exclude(is_intro=True)
            .order_by('order')
            .first()
        )
