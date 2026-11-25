"""Download the locally bundled product photographs used by products.csv."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data" / "products.csv"
LICENSE_URL = "https://unsplash.com/license"

# Each catalogue record gets a distinct, category-relevant Unsplash image.
IMAGE_IDS = {
    "P1001": "1587293823622-3a4743b0e601",
    "P1002": "1514228742587-6b1558fcca3d",
    "P1003": "1624272673361-335d488ef9f7",
    "P1004": "1637437757614-6491c8e915b5",
    "P1005": "1716369786765-5de0bb2d2658",
    "P1006": "1658869402195-9f0ea192ecd5",
    "P1007": "1507473885765-e6ed057f782c",
    "P1008": "1602143407151-7111542de6e8",
    "P1009": "1674621703172-ef68b33e52da",
    "P1010": "1679437654307-80ca842ea88e",
    "P1011": "1553062407-98eeb64c6a62",
    "P1012": "1584827386916-b5351d3ba34b",
    "P1013": "1760376789478-c1023d2dc007",
    "P1014": "1593618998160-e34014e67546",
    "P1015": "1511499767150-a48a237f0083",
    "P1016": "1661006670127-b560e732ce28",
    "P1017": "1509745651274-ddeb337c854a",
    "P1018": "1781971559730-3129f63d5bd7",
    "P1019": "1557363339-e4ea35792896",
    "P1020": "1613629758552-443027994609",
    "P1021": "1677515238009-a5e245703e74",
    "P1022": "1632794716789-42d9995fb5b6",
    "P1023": "1660051759835-91a79e5ab426",
    "P1024": "1637437411360-b4607d62ddd3",
    "P1025": "1716951918731-77d7682b4e63",
    "P1026": "1622560481336-b44c811b0958",
    "P1027": "1732613842353-0fccc5b72d51",
    "P1028": "1570222094114-d054a817e56b",
    "P1029": "1688578735122-f37256f1b8b0",
    "P1030": "1555041469-a586c61ea9bc",
    "P1031": "1556910602-38f53e68e15d",
    "P1032": "1573591276084-47884b4335f4",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download even if a file already exists")
    parser.add_argument("--only", nargs="+", help="download only these product IDs, retaining the other verified local files")
    args = parser.parse_args()
    with CATALOGUE.open("r", encoding="utf-8-sig", newline="") as handle:
        products = list(csv.DictReader(handle))
    ids = {row["product_id"] for row in products}
    if ids != set(IMAGE_IDS):
        raise SystemExit(f"Photo manifest/catalogue ID mismatch: missing={sorted(ids - set(IMAGE_IDS))}, extra={sorted(set(IMAGE_IDS) - ids)}")
    if len(set(IMAGE_IDS.values())) != len(IMAGE_IDS):
        raise SystemExit("Each product must have a distinct source photograph.")
    if args.only and not set(args.only) <= ids:
        raise SystemExit(f"Unknown product ID(s): {sorted(set(args.only) - ids)}")

    sources = []
    for product in products:
        photo_id = IMAGE_IDS[product["product_id"]]
        relative_path = product["image"].removeprefix("/storefront/")
        target = ROOT / "storefront" / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        misplaced = ROOT / "storefront" / relative_path.removeprefix("assets/")
        if not target.is_file() and misplaced.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            misplaced.replace(target)
        url = f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&fm=webp&w=720&h=720&q=78"
        should_download = args.force or (
            product["product_id"] in args.only if args.only else not target.is_file()
        )
        if args.only and product["product_id"] not in args.only and not target.is_file():
            raise SystemExit(f"Missing local photo outside --only selection: {target}")
        if should_download:
            request = urllib.request.Request(url, headers={"User-Agent": "SmartMarketplaceLocalDemo/1.0"})
            with urllib.request.urlopen(request, timeout=35) as response:
                content_type = response.headers.get_content_type()
                data = response.read()
            if content_type != "image/webp" or not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
                raise SystemExit(f"Unexpected image response for {product['product_id']}: {content_type}, {len(data)} bytes")
            if len(data) > 650_000:
                raise SystemExit(f"Optimized photograph exceeds 650 KB: {product['product_id']} ({len(data)} bytes)")
            target.write_bytes(data)
        data = target.read_bytes()
        if not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
            raise SystemExit(f"Invalid local WebP file: {target}")
        sources.append({
            "product_id": product["product_id"],
            "title": product["title"],
            "source": f"https://images.unsplash.com/photo-{photo_id}",
            "local_path": product["image"],
            "license": LICENSE_URL,
            "format": "WebP",
            "bytes": len(data),
        })
        print(f"{product['product_id']}: {target.relative_to(ROOT)} ({len(data)} bytes)")
        time.sleep(0.05)

    manifest = ROOT / "storefront" / "assets" / "product-images" / "SOURCES.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"license": LICENSE_URL, "images": sources}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified {len(sources)} distinct local WebP photos; source manifest: {manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
