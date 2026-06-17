import subprocess, os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'earthrise_applied_artificial_intelligence_and_deep_learning_book_django.settings'
django.setup()
from django.conf import settings
from bs4 import BeautifulSoup

for nb_path, label in [
    ('03_Semantic_Segmentation/03__Clay_Deforestation_Segmentation_Model/notebooks/ClayDeforestationv3.html', 'clay'),
    ('index.html', 'intro'),
]:
    result = subprocess.run(
        ['git', 'show', 'remotes/origin/gh-pages:' + nb_path],
        cwd=str(settings.NOTEBOOK_SOURCE_DIR), capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=30
    )
    if result.returncode != 0:
        print(label, 'NOT FOUND')
        continue
    soup = BeautifulSoup(result.stdout, 'html.parser')
    content = soup.find(id='quarto-document-content')
    print('=== ' + label + ' ===')
    for h in content.find_all(['h1','h2','h3'], limit=10):
        print('  ' + h.name + ' | id=' + str(h.get('id')) + ' | anchor=' + str(h.get('data-anchor-id')) + ' | ' + h.get_text()[:70])
    print()
