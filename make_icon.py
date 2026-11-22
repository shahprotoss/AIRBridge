"""Create AIRBridge artwork from vector-style drawing commands (no external assets)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets"


def create():
    OUT.mkdir(parents=True, exist_ok=True)
    size = 1024
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = base.load()
    for y in range(size):
        for x in range(size):
            amount = (x / size) * 0.4 + (1 - y / size) * 0.6
            px[x, y] = (
                round(16 + 51 * amount),
                round(103 + 65 * amount),
                round(218 + 35 * amount),
                255,
            )
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((28, 28, 996, 996), radius=220, fill=255)
    base.putalpha(mask)
    icon.alpha_composite(base)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((115, 85, 920, 850), fill=(255, 255, 255, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    icon.alpha_composite(glow)
    d = ImageDraw.Draw(icon)
    d.ellipse((190, 190, 834, 834), outline=(255, 255, 255, 65), width=11)
    # Paired forward/up and forward/down arrows communicate file handoff.
    d.arc((280, 292, 770, 770), start=203, end=334, fill=(255, 255, 255, 245), width=72)
    d.arc((255, 246, 739, 739), start=22, end=151, fill=(211, 237, 255, 255), width=72)
    d.polygon(((746, 292), (792, 513), (560, 453)), fill=(255, 255, 255, 255))
    d.polygon(((280, 744), (234, 523), (464, 585)), fill=(211, 237, 255, 255))
    # Downscale with high-quality antialiasing.
    icon.save(OUT / "airbridge.png")
    icon.save(
        OUT / "airbridge.ico", format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Created {OUT / 'airbridge.ico'}")


if __name__ == "__main__":
    create()
