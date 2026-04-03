"""Download 30 diverse arXiv PDFs to data/raw-pdfs/doc1.pdf … doc30.pdf.

Uses 6 thematic query buckets (5 papers each) to ensure layout diversity
across text-heavy, figure-heavy, table-heavy, and equation-heavy documents.

PDFs are downloaded into memory, trimmed to MAX_PAGES in memory, and only
the trimmed result is written to disk — the full file never touches storage.

Extra results are fetched per bucket so that failures have fallbacks.

Usage:
    python scripts/collect_pdfs.py --out-dir ./data/raw-pdfs --total 30
"""

from __future__ import annotations

import argparse
import io
import time
import urllib.request
from pathlib import Path

import arxiv
import pypdf


# 6 buckets × 5 papers = 30 total
QUERY_BUCKETS = [
    ("deep learning neural network", 5),
    ("survey machine learning", 5),
    ("natural language processing transformer", 5),
    ("computer vision object detection", 5),
    ("reinforcement learning policy gradient", 5),
    ("graph neural network attention mechanism", 5),
]

SLEEP_BETWEEN_DOWNLOADS = 3  # seconds — respect arxiv rate limits
MAX_PAGES = 15
# How many extra results to fetch per bucket as fallback candidates
FETCH_MULTIPLIER = 2

MIN_PDF_BYTES = 10 * 1024        # 10 KB — skip suspiciously small/corrupt files
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB — abort oversized streams


def search_arxiv(query: str, max_results: int = 5) -> list[arxiv.Result]:
    """Search arxiv and return result objects.

    Retries up to 3 times with long backoff on HTTP 429 rate-limit responses.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    for attempt in range(3):
        try:
            results = list(client.results(search))
            return results
        except arxiv.HTTPError as e:
            if e.status == 429 and attempt < 2:
                wait = 30 * (attempt + 1)  # 30s, 60s
                print(f"  WARN: arxiv rate limit (429) on search — waiting {wait}s before retry {attempt + 2}/3 …")
                time.sleep(wait)
            else:
                raise
    return []


def download_and_trim(result: arxiv.Result, dest_path: Path, max_pages: int = MAX_PAGES) -> bool:
    """Download a PDF into memory, trim to max_pages, write trimmed file to disk.

    Returns True on success. The full PDF is never written to disk.
    Retries up to 3 times with exponential backoff on transient failures.
    """
    pdf_url = result.pdf_url
    headers = {"User-Agent": "DocStruct-eval/1.0 (academic research)"}

    for attempt in range(3):
        try:
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                stream_buf = io.BytesIO()
                downloaded = 0
                while True:
                    chunk = resp.read(65536)  # 64 KB chunks
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > MAX_DOWNLOAD_BYTES:
                        raise ValueError(f"PDF exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB cap — skipping")
                    stream_buf.write(chunk)
                raw_bytes = stream_buf.getvalue()

            if len(raw_bytes) < MIN_PDF_BYTES:
                raise ValueError(f"PDF too small ({len(raw_bytes)} bytes) — likely corrupt or empty")

            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            total_pages = len(reader.pages)
            pages_to_keep = min(total_pages, max_pages)

            writer = pypdf.PdfWriter()
            for i in range(pages_to_keep):
                writer.add_page(reader.pages[i])

            buf = io.BytesIO()
            writer.write(buf)
            dest_path.write_bytes(buf.getvalue())

            trimmed_note = f" (trimmed {total_pages}→{pages_to_keep} pages)" if total_pages > max_pages else f" ({total_pages} pages)"
            size_kb = dest_path.stat().st_size // 1024
            print(f"         → saved {dest_path.name} ({size_kb} KB){trimmed_note}")
            return True

        except Exception as e:
            wait = 2 ** attempt * 5  # 5s, 10s, 20s
            if attempt < 2:
                print(f"  WARN: attempt {attempt + 1}/3 failed for {result.entry_id}: {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                print(f"  WARN: failed to download {result.entry_id} → {dest_path.name}: {e}")

    return False


def collect_pdfs(output_dir: Path, total: int = 30) -> None:
    """Fetch PDFs across query buckets and save as doc1.pdf … docN.pdf.

    Idempotent: skips files that already exist on disk.
    Fetches extra results per bucket so failures have fallback candidates.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_num = 1
    failures: list[str] = []

    for query, count in QUERY_BUCKETS:
        if doc_num > total:
            break

        fetch_count = count * FETCH_MULTIPLIER
        print(f"\n[Bucket] query='{query}' requesting {count} papers (fetching {fetch_count} candidates) …")
        results = search_arxiv(query, max_results=fetch_count)
        time.sleep(3)  # respect arxiv search API rate limits

        if len(results) < count:
            print(f"  WARN: only {len(results)} results for query '{query}'")

        bucket_saved = 0
        for result in results:
            if doc_num > total or bucket_saved >= count:
                break

            dest_path = output_dir / f"doc{doc_num}.pdf"

            if dest_path.exists() and dest_path.stat().st_size > 1024:
                print(f"  [{doc_num:02d}/{total}] skip (exists): {dest_path.name}")
                doc_num += 1
                bucket_saved += 1
                continue

            title_short = result.title[:60].replace("\n", " ")
            print(f"  [{doc_num:02d}/{total}] {result.entry_id} — {title_short}")

            ok = download_and_trim(result, dest_path)
            if ok:
                doc_num += 1
                bucket_saved += 1
            else:
                failures.append(result.entry_id)
                # don't increment — try next fallback candidate in this bucket

            time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    total_downloaded = doc_num - 1
    print(f"\n{'='*50}")
    print(f"Done. {total_downloaded}/{total} PDFs saved to {output_dir}")
    if failures:
        print(f"Failed downloads ({len(failures)}): {', '.join(failures)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download 30 diverse arXiv PDFs for DocStruct evaluation"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/raw-pdfs"),
        help="Output directory (default: data/raw-pdfs)",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=5,
        help="Total number of PDFs to collect (default: 30)",
    )
    args = parser.parse_args()
    collect_pdfs(args.out_dir, args.total)


if __name__ == "__main__":
    main()
