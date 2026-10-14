import re


ALIASES = {
    "香港": ("香港", "Hong Kong", "HongKong", "HK", "HKG", "🇭🇰"),
    "新加坡": ("新加坡", "Singapore", "SG", "SIN", "🇸🇬"),
}


def excluded_region(name: str, regions: list[str]) -> str | None:
    for region in regions:
        canonical = next((key for key, aliases in ALIASES.items()
                          if region.casefold() in [a.casefold() for a in aliases]), region)
        for alias in ALIASES.get(canonical, (region,)):
            if alias.isascii():
                # Digits and separators may follow country codes, letters may not.
                if re.search(r"(?<![a-zA-Z])" + re.escape(alias).replace(r"\ ", r"\s*") + r"(?![a-zA-Z])", name, re.I):
                    return canonical
            elif alias in name:
                return canonical
    return None
