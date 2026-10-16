"""Generate pinned static UI faces; fontTools is not a runtime dependency."""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parent.parent
DIRECTORY = ROOT / "resources" / "fonts"
FAMILY = "Clash Sans SC"
FACES = ((400, "Regular"), (500, "Medium"), (600, "SemiBold"))


def main():
    for weight, style in FACES:
        source = TTFont(DIRECTORY / "NotoSansSC-VF.ttf", recalcTimestamp=False)
        font = instantiateVariableFont(source, {"wght": weight}, inplace=True)
        # No variation axes remain. An empty STAT can make DirectWrite classify
        # all instances as Regular despite their OS/2 weight and name records.
        if "STAT" in font:
            del font["STAT"]
        # A distinct family prevents installed variable faces from winning Qt matching.
        # Windows legacy families only link Regular/Bold/Italic. Give intermediate
        # weights separate legacy names while grouping them typographically.
        legacy_family = f"{FAMILY} {style}" if weight == 500 else FAMILY
        names = {1: legacy_family, 2: "Bold" if weight == 600 else "Regular", 3: f"{FAMILY}-{style}-static",
                 4: f"{FAMILY} {style}", 6: f"ClashSansSC-{style}",
                 16: FAMILY, 17: style}
        for entry in list(font["name"].names):
            if entry.nameID in names:
                font["name"].removeNames(entry.nameID, entry.platformID,
                                         entry.platEncID, entry.langID)
        for name_id, value in names.items():
            font["name"].setName(value, name_id, 3, 1, 0x409)
        font["OS/2"].usWeightClass = weight
        font["OS/2"].fsSelection &= ~(1 << 5)
        if weight == 400:
            font["OS/2"].fsSelection |= 1 << 6
        else:
            font["OS/2"].fsSelection &= ~(1 << 6)
        font["head"].macStyle &= ~1
        if weight == 600:
            font["OS/2"].fsSelection |= 1 << 5
            font["head"].macStyle |= 1
        output = DIRECTORY / f"ClashSansSC-{style}.ttf"
        font.save(output)
        font.close()
        print(f"Generated {output.name} ({weight})")


if __name__ == "__main__":
    main()
