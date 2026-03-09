from bs4 import BeautifulSoup

with open('d:/Stackstorage/antigravity/nieuwsfeed/.tmp/mmc.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    for a in soup.select('a'):
        href = a.get('href', '')
        if 'nieuws' in href:
            parent = a.find_parent('div')
            p_class = parent.get('class') if parent else None
            print(f"A class: {a.get('class')}, Parent div class: {p_class}, Href: {href}")
