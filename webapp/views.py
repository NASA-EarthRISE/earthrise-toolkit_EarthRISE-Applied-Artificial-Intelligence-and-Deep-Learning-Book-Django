from django.shortcuts import render, get_object_or_404

from .models import Chapter


def home(request):
    intro = get_object_or_404(Chapter, is_intro=True)
    return render(request, 'home.html', {'chapter': intro})


def chapter(request, slug):
    ch = get_object_or_404(Chapter, slug=slug)
    return render(request, 'chapter.html', {'chapter': ch})
