import re


ALIASES = {
    "香港": ("香港", "Hong Kong", "HongKong", "HK", "HKG", "🇭🇰"),
    "新加坡": ("新加坡", "Singapore", "SG", "SIN", "🇸🇬"),
    "日本": ("日本", "Japan", "JP", "JPN", "🇯🇵"),
    "美国": ("美国", "United States", "USA", "US", "🇺🇸"),
    "德国": ("德国", "Germany", "DE", "DEU", "🇩🇪"),
    "英国": ("英国", "United Kingdom", "UK", "GB", "GBR", "🇬🇧"),
    "韩国": ("韩国", "South Korea", "Korea", "KR", "KOR", "🇰🇷"),
    "台湾": ("台湾", "Taiwan", "TW", "TWN", "🇹🇼"),
    "澳门": ("澳门", "Macao", "Macau", "MO", "MAC", "🇲🇴"),
    "加拿大": ("加拿大", "Canada", "CA", "CAN", "🇨🇦"),
    "澳大利亚": ("澳大利亚", "澳洲", "Australia", "AU", "AUS", "🇦🇺"),
    "法国": ("法国", "France", "FR", "FRA", "🇫🇷"),
    "荷兰": ("荷兰", "Netherlands", "NL", "NLD", "🇳🇱"),
    "俄罗斯": ("俄罗斯", "Russia", "RU", "RUS", "🇷🇺"),
    "印度": ("印度", "India", "IN", "IND", "🇮🇳"),
    "土耳其": ("土耳其", "Turkey", "Türkiye", "TR", "TUR", "🇹🇷"),
    "越南": ("越南", "Vietnam", "VN", "VNM", "🇻🇳"),
    "泰国": ("泰国", "Thailand", "TH", "THA", "🇹🇭"),
    "马来西亚": ("马来西亚", "Malaysia", "MY", "MYS", "🇲🇾"),
    "菲律宾": ("菲律宾", "Philippines", "PH", "PHL", "🇵🇭"),
    "印度尼西亚": ("印度尼西亚", "印尼", "Indonesia", "ID", "IDN", "🇮🇩"),
    "巴西": ("巴西", "Brazil", "BR", "BRA", "🇧🇷"),
    "阿根廷": ("阿根廷", "Argentina", "AR", "ARG", "🇦🇷"),
    "南非": ("南非", "South Africa", "ZA", "ZAF", "🇿🇦"),
    "瑞士": ("瑞士", "Switzerland", "CH", "CHE", "🇨🇭"),
    "瑞典": ("瑞典", "Sweden", "SE", "SWE", "🇸🇪"),
    "芬兰": ("芬兰", "Finland", "FI", "FIN", "🇫🇮"),
    "挪威": ("挪威", "Norway", "NO", "NOR", "🇳🇴"),
    "意大利": ("意大利", "Italy", "IT", "ITA", "🇮🇹"),
    "西班牙": ("西班牙", "Spain", "ES", "ESP", "🇪🇸"),
    "新西兰": ("新西兰", "New Zealand", "NZ", "NZL", "🇳🇿"),
    "阿联酋": ("阿联酋", "United Arab Emirates", "UAE", "AE", "🇦🇪"),
}


def _matches_alias(name: str, alias: str) -> bool:
    if alias.isascii():
        # Digits and separators may follow country codes, letters may not.
        return bool(re.search(r"(?<![a-zA-Z])" + re.escape(alias).replace(r"\ ", r"\s*")
                              + r"(?![a-zA-Z])", name, re.I))
    if alias == "印度":
        return bool(re.search(r"印度(?!尼西亚)", name))
    return alias in name


def available_regions(node_names: list[str]) -> list[str]:
    """Only offer regions recognized in actual direct members of the selected group."""
    return list(dict.fromkeys(region for name in node_names for region, aliases in ALIASES.items()
                              if any(_matches_alias(name, alias) for alias in aliases)))


def excluded_region(name: str, regions: list[str]) -> str | None:
    for region in regions:
        canonical = next((key for key, aliases in ALIASES.items()
                          if region.casefold() in [a.casefold() for a in aliases]), region)
        for alias in ALIASES.get(canonical, (region,)):
            if _matches_alias(name, alias):
                return canonical
    return None
