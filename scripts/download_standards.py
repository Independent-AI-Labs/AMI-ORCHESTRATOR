import re
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "compliance/docs/COMPLIANCE_STANDARDS_CATALOG.md"
DOWNLOAD_DIR = ROOT / "compliance/docs/compliance_standards"
REQUEST_TIMEOUT = 30


def download_pdfs() -> None:
    """Download reference PDFs listed in the compliance standards catalog."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    content = CATALOG_PATH.read_text(encoding="utf-8")
    pdf_links = re.findall(r"\*\s*\*\*PDF Link:\*\*\s*\[[^\]]+\]\(([^)]+)\)", content)

    for link in pdf_links:
        try:
            response = requests.get(link, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            filename = _resolve_filename(link)
            filename.write_bytes(response.content)
            print(f"Successfully downloaded {filename.name}")

        except requests.exceptions.RequestException as exc:
            print(f"Error downloading {link}: {exc}")


def _resolve_filename(link: str) -> Path:
    """Return the destination path for a downloaded PDF."""
    parsed = urlparse(link)
    name = Path(parsed.path).name or "downloaded.pdf"
    return DOWNLOAD_DIR / name


if __name__ == "__main__":
    download_pdfs()
