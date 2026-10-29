"""Export clean native icons from the retained image-generated HD master."""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, PngImagePlugin


ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "resources"
MASTER = DIRECTORY / "app-master.png"
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
# Standard export geometry, measured inside the generated tile. The master is
# never overwritten. User authorized this alpha-boundary cleanup on 2026-10-28.
MASK_REFERENCE_SIZE = 1254
MASK_BOUNDS = (96, 96, 1158, 1158)
MASK_RADIUS = 250
MASK_SUPERSAMPLING = 4


def export_icon(image, size):
    scale = size * MASK_SUPERSAMPLING / MASK_REFERENCE_SIZE
    mask = Image.new("L", (size * MASK_SUPERSAMPLING,) * 2, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        tuple(round(value * scale) for value in MASK_BOUNDS),
        radius=round(MASK_RADIUS * scale), fill=255,
    )
    # BOX antialiasing preserves a clean finite silhouette without the ringing
    # that a sharp reconstruction filter can add outside an alpha boundary.
    mask = mask.resize((size, size), Image.Resampling.BOX)
    result = image.resize((size, size), Image.Resampling.LANCZOS)
    result.putalpha(ImageChops.multiply(result.getchannel("A"), mask))
    return result


def main():
    if not MASTER.is_file():
        raise SystemExit("Missing resources/app-master.png; restore the committed icon master before building.")
    with Image.open(MASTER) as source:
        if source.width != source.height or min(source.size) < 1024:
            raise SystemExit("App icon master must be square and at least 1024px.")
        image = source.convert("RGBA")
        generation_prompt = source.info.get("GenerationPrompt", "See resources/app-icon-prompt.md.")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Source", "Image-generated flow-ribbon master: resources/app-master.png; built-in imagegen; see resources/app-icon-prompt.md.")
    metadata.add_text("Conversion", "scripts/make_icon.py; Pillow LANCZOS color resampling; 4x BOX-antialiased standard rounded-square alpha mask, user-authorized on 2026-10-28.")
    metadata.add_text("ExportMask", f"Reference {MASK_REFERENCE_SIZE}px; bounds {MASK_BOUNDS}; corner radius {MASK_RADIUS}px; original master retained.")
    metadata.add_text("GenerationPrompt", generation_prompt)
    export_icon(image, 1024).save(DIRECTORY / "app-icon.png", pnginfo=metadata)
    frames = [export_icon(image, size) for size in ICON_SIZES]
    frames[-1].save(DIRECTORY / "app.png", pnginfo=metadata)
    frames[-1].save(DIRECTORY / "app.ico", format="ICO",
                    sizes=[(size, size) for size in ICON_SIZES], append_images=frames[:-1])
    print(f"Exported clean app-icon.png (1024px), app.png and {len(ICON_SIZES)} ICO sizes; retained {MASTER.name}")


if __name__ == "__main__":
    main()
