from django.db.models import Min

from .models import Part, Chapter


def navigation(request):
    """
    Inject chapter navigation structure into every template context.

    Returns ``nav_items``: a list of dicts ordered by book sequence.
    Each item has a ``type`` key of either 'chapter' or 'part'.
    """
    nav_items = []

    # Standalone chapters (no part, not intro)
    for ch in Chapter.objects.filter(part__isnull=True, is_intro=False).order_by('order'):
        nav_items.append({'type': 'chapter', 'obj': ch, 'order': ch.order})

    # Parts ordered by the minimum order of their chapters
    for part in Part.objects.prefetch_related('chapters').annotate(
        min_order=Min('chapters__order')
    ).order_by('min_order'):
        nav_items.append({'type': 'part', 'obj': part, 'order': part.min_order or 99})

    # Sort the combined list by order so standalone chapters interleave with parts
    nav_items.sort(key=lambda x: x['order'])

    intro = Chapter.objects.filter(is_intro=True).first()

    return {
        'nav_items': nav_items,
        'nav_intro': intro,
    }
