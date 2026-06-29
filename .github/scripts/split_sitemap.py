"""Split MkDocs sitemap.xml into per-section sitemaps + sitemap index."""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import date

NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

SITE_DIR = Path("site")
SITEMAP_PATH = SITE_DIR / "sitemap.xml"
TODAY = date.today().isoformat()
SITE_URL = "https://rules.omnisgm.com/"


def classify(loc: str) -> str:
    """Map URL to section bucket name."""
    path = loc.replace(SITE_URL, "").lstrip("en/")
    if path.startswith("daggerheart/"):
        return "sitemap-daggerheart"
    if path.startswith("dnd/srd-5.2/"):
        return "sitemap-dnd-srd52"
    if path.startswith("dnd/srd-5.1/"):
        return "sitemap-dnd-srd51"
    if path.startswith("dnd/"):
        return "sitemap-dnd-other"
    return "sitemap-general"


def run():
    ET.register_namespace("", NS["sm"])
    ET.register_namespace("xhtml", NS["xhtml"])

    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()

    buckets: dict[str, list[ET.Element]] = {}
    for url_el in root.findall("sm:url", NS):
        loc = url_el.find("sm:loc", NS)
        if loc is None or loc.text is None:
            continue
        bucket = classify(loc.text)
        buckets.setdefault(bucket, []).append(url_el)

    # Write individual sitemaps
    written = []
    for name, urls in sorted(buckets.items()):
        urlset = ET.Element(f"{{{NS['sm']}}}urlset")
        for u in urls:
            urlset.append(u)
        out = SITE_DIR / f"{name}.xml"
        et = ET.ElementTree(urlset)
        ET.indent(et, space="    ")
        et.write(out, xml_declaration=True, encoding="UTF-8")
        written.append(name)
        print(f"  {name}.xml — {len(urls)} URLs")

    # Write sitemap index
    idx = ET.Element(f"{{{NS['sm']}}}sitemapindex")
    for name in sorted(written):
        sm_el = ET.SubElement(idx, f"{{{NS['sm']}}}sitemap")
        ET.SubElement(sm_el, f"{{{NS['sm']}}}loc").text = f"{SITE_URL}{name}.xml"
        ET.SubElement(sm_el, f"{{{NS['sm']}}}lastmod").text = TODAY
    idx_tree = ET.ElementTree(idx)
    ET.indent(idx_tree, space="    ")
    idx_tree.write(SITEMAP_PATH, xml_declaration=True, encoding="UTF-8")
    print(f"\nsitemap.xml — index with {len(written)} sitemaps")


if __name__ == "__main__":
    run()
