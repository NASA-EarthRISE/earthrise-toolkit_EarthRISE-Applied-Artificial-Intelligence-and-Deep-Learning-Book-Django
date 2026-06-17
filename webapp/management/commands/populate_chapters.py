"""
Management command: populate_chapters

Creates/updates Part and Chapter records from the _quarto.yml chapter structure.
Idempotent — safe to run multiple times.
"""
from django.core.management.base import BaseCommand
from webapp.models import Part, Chapter


# Chapter data derived from _quarto.yml
# Format: (order, title, slug, content_type, source_path, notebook_filename, part_slug, is_intro)
PARTS = [
    {'title': 'Semantic Segmentation',                    'slug': 'semantic-segmentation',              'order': 1},
    {'title': 'Time Series',                              'slug': 'time-series',                        'order': 2},
    {'title': 'Future of Deep Learning & Foundation Models', 'slug': 'future-deep-learning',            'order': 3},
]

CHAPTERS = [
    {
        'order': 0,
        'title': 'Introduction',
        'slug': 'introduction',
        'content_type': 'markdown',
        'source_path': 'index.md',
        'notebook_filename': '',
        'part_slug': None,
        'is_intro': True,
    },
    {
        'order': 1,
        'title': 'Data Preparation',
        'slug': 'data-preparation',
        'content_type': 'notebook',
        'source_path': '02_Data_Preparation/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 2.1,
        'title': 'Crop Mapping',
        'slug': 'crop-mapping',
        'content_type': 'notebook',
        'source_path': '03_Semantic_Segmentation/01__Crop_Mapping/notebooks/Rice_Mapping_Bhutan_2021.ipynb',
        'notebook_filename': 'Rice_Mapping_Bhutan_2021.ipynb',
        'part_slug': 'semantic-segmentation',
        'is_intro': False,
    },
    {
        'order': 2.2,
        'title': 'Selective Logging Detection',
        'slug': 'selective-logging-detection',
        'content_type': 'notebook',
        'source_path': '03_Semantic_Segmentation/02__Selective_Logging_Detection/notebooks/Selective_Logging_Detection.ipynb',
        'notebook_filename': 'Selective_Logging_Detection.ipynb',
        'part_slug': 'semantic-segmentation',
        'is_intro': False,
    },
    {
        'order': 2.3,
        'title': 'Clay Deforestation Segmentation',
        'slug': 'clay-deforestation-segmentation',
        'content_type': 'notebook',
        'source_path': '03_Semantic_Segmentation/03__Clay_Deforestation_Segmentation_Model/notebooks/ClayDeforestationv3.ipynb',
        'notebook_filename': 'ClayDeforestationv3.ipynb',
        'part_slug': 'semantic-segmentation',
        'is_intro': False,
    },
    {
        'order': 3,
        'title': 'Object Detection',
        'slug': 'object-detection',
        'content_type': 'notebook',
        'source_path': '04_Object_Detection/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 4.1,
        'title': 'Soybean Yield Prediction',
        'slug': 'soybean-yield-prediction',
        'content_type': 'notebook',
        'source_path': '05_Time_Series/01__Soybean_Yield_Prediction/notebooks/Crop_yield_estimationR4.ipynb',
        'notebook_filename': 'Crop_yield_estimationR4.ipynb',
        'part_slug': 'time-series',
        'is_intro': False,
    },
    {
        'order': 5,
        'title': 'Active Fire Detection',
        'slug': 'active-fire-detection',
        'content_type': 'notebook',
        'source_path': '06_Eco_Process_Sim/01__Active_Fire_Detection/notebooks/BNN_Active_Fire_Detection.ipynb',
        'notebook_filename': 'BNN_Active_Fire_Detection.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 6,
        'title': 'Transfer Learning',
        'slug': 'transfer-learning',
        'content_type': 'notebook',
        'source_path': '07_Transfer_Learning/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 7,
        'title': 'Fusion',
        'slug': 'fusion',
        'content_type': 'notebook',
        'source_path': '08_Fusion/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 8,
        'title': 'Downscaling',
        'slug': 'downscaling',
        'content_type': 'notebook',
        'source_path': '09_Downscaling/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 9.1,
        'title': 'Evaluating Foundation Models',
        'slug': 'evaluating-foundation-models',
        'content_type': 'notebook',
        'source_path': '10_Future/01__Evaluating_Foundation_Models_Trained_with_Earth_Observation_Data/notebooks/Chapter_Practical_EOFM_Evaluation.ipynb',
        'notebook_filename': 'Chapter_Practical_EOFM_Evaluation.ipynb',
        'part_slug': 'future-deep-learning',
        'is_intro': False,
    },
    {
        'order': 10,
        'title': 'Ethics of AI',
        'slug': 'ethics-of-ai',
        'content_type': 'notebook',
        'source_path': '11_Ethics/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
    {
        'order': 11,
        'title': 'Conclusions',
        'slug': 'conclusions',
        'content_type': 'notebook',
        'source_path': '12_Conclusions/index.ipynb',
        'notebook_filename': 'index.ipynb',
        'part_slug': None,
        'is_intro': False,
    },
]


class Command(BaseCommand):
    help = 'Populate the database with Part and Chapter records from _quarto.yml structure.'

    def handle(self, *args, **options):
        self.stdout.write('Creating/updating Parts...')
        part_map = {}
        for p in PARTS:
            obj, created = Part.objects.update_or_create(
                slug=p['slug'],
                defaults={'title': p['title'], 'order': p['order']},
            )
            part_map[p['slug']] = obj
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {obj.title}')

        self.stdout.write('Creating/updating Chapters...')
        for c in CHAPTERS:
            part = part_map.get(c['part_slug']) if c['part_slug'] else None
            obj, created = Chapter.objects.update_or_create(
                slug=c['slug'],
                defaults={
                    'title': c['title'],
                    'order': c['order'],
                    'content_type': c['content_type'],
                    'source_path': c['source_path'],
                    'notebook_filename': c['notebook_filename'],
                    'part': part,
                    'is_intro': c['is_intro'],
                },
            )
            status = 'Created' if created else 'Updated'
            part_name = part.title if part else '—'
            self.stdout.write(f'  {status}: [{part_name}] {obj.title}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {Part.objects.count()} parts, {Chapter.objects.count()} chapters.'
        ))
