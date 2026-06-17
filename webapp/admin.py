from django.contrib import admin
from .models import Part, Chapter


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'order')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order',)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'part', 'order', 'content_type', 'is_intro', 'notebook_filename')
    list_filter = ('part', 'content_type', 'is_intro')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('order',)
    search_fields = ('title', 'slug')
    readonly_fields = ('html_content',)
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'part', 'order', 'is_intro'),
        }),
        ('Content', {
            'fields': ('content_type', 'source_path', 'notebook_filename'),
        }),
        ('Rendered HTML (auto-generated)', {
            'fields': ('html_content',),
            'classes': ('collapse',),
        }),
    )
