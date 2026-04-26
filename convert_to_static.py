"""
Convert Django templates in frontend/pages/ to standalone static HTML
for GitHub Pages deployment. Creates static versions alongside originals
by writing to a temporary output, then replacing the originals.

This script:
1. Reads base.html to extract the shell (head, header, nav, etc.)
2. For each page template, strips Django tags and inserts content into the shell
3. Writes standalone HTML with relative ./frontend/ paths
"""
import re
import os

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(REPO_ROOT, "frontend", "pages")
TEMPLATES_DIR = os.path.join(REPO_ROOT, "templates")

# Pages to convert (filename -> extra CSS file basename)
PAGES = {
    "about.html": {"css": "about.css", "title": "About Us", "body_class": ""},
    "packages.html": {"css": "packages.css", "title": "Packages", "body_class": ""},
    "shark_key.html": {"css": "shark.css", "title": "Shark Species Recognition", "body_class": ""},
    "shark_cnn.html": {"css": "shark.css", "title": "Shark Species CNN", "body_class": "shark-cnn-view"},
    "shark_tutorial.html": {"css": "shark.css", "title": "YOLO11 Tutorial", "body_class": "shark-cnn-view"},
    "dashboard.html": {"css": "dashboard.css", "title": "Dashboard", "body_class": ""},
}

# Relative path from frontend/pages/ back to repo root
REL = "../../"

def static_path(match):
    """Replace {% static 'path' %} with relative path."""
    path = match.group(1)
    return f"{REL}frontend/{path}"

def strip_django_tags(content):
    """Remove/replace Django template tags."""
    # Remove {% extends %}, {% load %}, {% block %}, {% endblock %}, {% csrf_token %}
    content = re.sub(r'\{%\s*extends\s+[^%]+%\}', '', content)
    content = re.sub(r'\{%\s*load\s+[^%]+%\}', '', content)
    content = re.sub(r'\{%\s*block\s+\w+\s*%\}', '', content)
    content = re.sub(r'\{%\s*endblock\s*%\}', '', content)
    content = re.sub(r'\{%\s*csrf_token\s*%\}', '', content)
    
    # Replace {% static 'xxx' %} with relative paths
    content = re.sub(r"\{%\s*static\s+'([^']+)'\s*%\}", static_path, content)
    content = re.sub(r'\{%\s*static\s+"([^"]+)"\s*%\}', static_path, content)
    
    # Replace {% url 'name' %} with static page paths
    url_map = {
        'home': f'{REL}index.html',
        'packages': 'packages.html',
        'about': 'about.html',
        'login': '#',
        'register': '#',
        'dashboard': 'dashboard.html',
        'logout': '#',
        'shark_key': 'shark_key.html',
        'shark_cnn': 'shark_cnn.html',
        'shark_tutorial': 'shark_tutorial.html',
        'google_login_start': '#',
    }
    
    def url_replace(m):
        name = m.group(1)
        return url_map.get(name, '#')
    
    content = re.sub(r"\{%\s*url\s+'(\w+)'\s*%\}", url_replace, content)
    content = re.sub(r'\{%\s*url\s+"(\w+)"\s*%\}', url_replace, content)
    
    # Remove {% if ... %}, {% else %}, {% endif %}, {% for %}, {% endfor %} blocks
    # But keep the content between them (show non-authenticated version)
    content = re.sub(r'\{%\s*if\s+[^%]+%\}', '', content)
    content = re.sub(r'\{%\s*else\s*%\}', '', content)
    content = re.sub(r'\{%\s*endif\s*%\}', '', content)
    content = re.sub(r'\{%\s*for\s+[^%]+%\}', '', content)
    content = re.sub(r'\{%\s*endfor\s*%\}', '', content)
    
    # Replace {{ variable }} with empty or placeholder
    content = re.sub(r'\{\{\s*user\.username\s*\}\}', 'Guest', content)
    content = re.sub(r'\{\{\s*auth_profile\.credits\s*\}\}', '—', content)
    content = re.sub(r'\{\{\s*auth_profile\.email\s*\}\}', '—', content)
    content = re.sub(r'\{\{\s*active_users_count\s*\}\}', '—', content)
    content = re.sub(r'\{\{\s*total_users\s*\}\}', '—', content)
    content = re.sub(r"\{\{\s*shark_resources\.\w+\|default:'([^']*)'\s*\}\}", r'\1', content)
    content = re.sub(r'\{\{\s*[^}]+\s*\}\}', '', content)
    
    # Remove any remaining {% ... %} tags
    content = re.sub(r'\{%[^%]*%\}', '', content)
    
    return content

def build_page(filename, config):
    """Build a standalone HTML page."""
    src = os.path.join(PAGES_DIR, filename)
    if not os.path.exists(src):
        print(f"  SKIP: {filename} not found")
        return None
    
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip Django tags from the page content
    content = strip_django_tags(content)
    
    # Clean up excessive blank lines
    content = re.sub(r'\n{4,}', '\n\n', content)
    content = content.strip()
    
    extra_css = f'\n    <link rel="stylesheet" href="{REL}frontend/css/pages/{config["css"]}" />' if config.get("css") else ""
    body_class = f' class="{config["body_class"]}"' if config.get("body_class") else ""
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{config["title"]}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fjalla+One&family=Inter:wght@300;400;500;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{REL}frontend/css/style.css" />{extra_css}
    <script defer src="{REL}frontend/javascript/main.js"></script>
</head>
<body{body_class}>
    <canvas id="liquid-canvas" aria-hidden="true"></canvas>
    <div class="ambient-layer"></div>

    <header class="glass nav-wrap">
        <div class="nav-brand">SERRAFINS</div>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="main-navigation" aria-label="Open menu">
            <span></span>
            <span></span>
            <span></span>
        </button>
        <nav id="main-navigation" class="main-nav">
            <a href="{REL}index.html">Home</a>
            <a href="packages.html">Packages</a>
            <a href="about.html">About</a>
            <a href="dashboard.html">Dashboard</a>
        </nav>
    </header>

    <main class="page-shell">
{content}
    </main>
</body>
</html>
'''
    return html

def main():
    # First, backup Django templates to templates/ dir
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    
    for filename in PAGES:
        src = os.path.join(PAGES_DIR, filename)
        dst = os.path.join(TEMPLATES_DIR, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            with open(src, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(original)
            print(f"  Backed up: {filename} -> templates/{filename}")
    
    # Also backup base.html
    base_src = os.path.join(PAGES_DIR, "base.html")
    base_dst = os.path.join(TEMPLATES_DIR, "base.html")
    if os.path.exists(base_src) and not os.path.exists(base_dst):
        with open(base_src, 'r', encoding='utf-8') as f:
            original = f.read()
        with open(base_dst, 'w', encoding='utf-8') as f:
            f.write(original)
        print(f"  Backed up: base.html -> templates/base.html")
    
    # Also backup login.html and register.html
    for extra in ["login.html", "register.html"]:
        esrc = os.path.join(PAGES_DIR, extra)
        edst = os.path.join(TEMPLATES_DIR, extra)
        if os.path.exists(esrc) and not os.path.exists(edst):
            with open(esrc, 'r', encoding='utf-8') as f:
                original = f.read()
            with open(edst, 'w', encoding='utf-8') as f:
                f.write(original)
            print(f"  Backed up: {extra} -> templates/{extra}")
    
    # Now generate static versions
    for filename, config in PAGES.items():
        print(f"Converting {filename}...")
        html = build_page(filename, config)
        if html:
            out = os.path.join(PAGES_DIR, filename)
            with open(out, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Written: frontend/pages/{filename}")
    
    print("\nDone! Django templates backed up to templates/")
    print("Static versions written to frontend/pages/")

if __name__ == "__main__":
    main()
