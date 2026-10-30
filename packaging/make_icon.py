"""Génère l'icône d'OpenPLS (PNG, ICO pour Windows, ICNS pour macOS) : python packaging/make_icon.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out = Path(__file__).parent
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([40, 40, S - 40, S - 40], radius=220, fill=(46, 94, 158, 255))
# deux ellipses reliées par une flèche : une variable latente qui en explique une autre
d.ellipse([150, 300, 450, 520], outline="white", width=44)
d.ellipse([574, 300, 874, 520], outline="white", width=44)
d.line([470, 410, 520, 410], fill="white", width=44)
d.polygon([(510, 362), (560, 410), (510, 458)], fill="white")
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 210)
except OSError:
    font = ImageFont.load_default()
d.text((S / 2, 760), "PLS", fill="white", font=font, anchor="mm")
img.save(out / "icon.png")
img.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(out / "icon.icns")
print("icône générée")
