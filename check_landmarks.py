import urllib.request
import re

def check_page(url, label):
    with urllib.request.urlopen(url) as r:
        html = r.read().decode('utf-8', errors='replace')
    mains = re.findall(r'<main[^>]*>', html, re.I)
    headers = re.findall(r'<header[^>]*>', html, re.I)
    footers = re.findall(r'<footer[^>]*>', html, re.I)
    sections_with_aria = re.findall(r'<section[^>]+aria-label[^>]*>', html, re.I)
    print('\n=== ' + label + ' ===')
    print('MAINS (' + str(len(mains)) + '):', mains)
    print('HEADERS (' + str(len(headers)) + '):', headers)
    print('FOOTERS (' + str(len(footers)) + '):', footers)
    print('SECTIONS with aria-label (' + str(len(sections_with_aria)) + '):', sections_with_aria[:3])

check_page('http://127.0.0.1:8080/', 'HOME')
check_page('http://127.0.0.1:8080/chapter/data-preparation/', 'data-preparation')
