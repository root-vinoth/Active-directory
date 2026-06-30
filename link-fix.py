import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage:")
    print("python fix_images.py <markdown_file> <image_folder>")
    print("Example:")
    print("python fix_images.py Attacks\\smb-share-access.md smb")
    sys.exit(1)

md_file = Path(sys.argv[1])
image_folder = sys.argv[2]

if not md_file.exists():
    print(f"File not found: {md_file}")
    sys.exit(1)

text = md_file.read_text(encoding="utf-8")


def convert_image(match):
    image = match.group(1).strip()

    # Already a URL or already has a relative path
    if image.startswith("http") or "/" in image or "\\" in image:
        return match.group(0)

    return f"![](../image/{image_folder}/{image})"


# -------------------------------------------------
# Convert Obsidian Wiki Links
# ![[image.png]]
# -------------------------------------------------
text = re.sub(
    r'!\[\[([^\]]+\.(?:png|jpg|jpeg|gif|webp|svg))\]\]',
    convert_image,
    text,
)

# -------------------------------------------------
# Convert Markdown image links
# ![](image.png)
# -------------------------------------------------
text = re.sub(
    r'!\[\]\(([^)]+\.(?:png|jpg|jpeg|gif|webp|svg))\)',
    convert_image,
    text,
)

md_file.write_text(text, encoding="utf-8")

print("✔ Image links converted successfully.")