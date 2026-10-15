from pathlib import Path
from PIL import Image

FOLDER = Path("static/img/login")
MAX_WIDTH = 1920
QUALITY = 80

for path in sorted(FOLDER.glob("*.jpg")):
    before = path.stat().st_size
    img = Image.open(path).convert("RGB")
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    img.save(path, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    after = path.stat().st_size
    print(f"{path.name}: {before/1024:.0f} KB -> {after/1024:.0f} KB")