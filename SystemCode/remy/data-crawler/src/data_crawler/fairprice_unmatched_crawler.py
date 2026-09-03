#!/usr/bin/env python3
"""
FairPrice search crawler for the unmatched head terms.

The category crawl (fairprice_crawler.py) covers the five aisles in
CRAWL_INSTRUCT.md; whatever nutrient row it cannot price is summarised in
data/unmatched_food.csv as (name, occurrences). This script goes after those
terms one by one:

    https://www.fairprice.com.sg/search?query=<term>

and parses the results with the same DOM contract -- the search grid renders
the identical PRODUCT_IMPRESSION cards, so extraction is imported wholesale
from fairprice_crawler rather than restated here.

Unlike a category page, the search grid's first ~20 cards are server-rendered
and they are the ones that matter (results past the first screen have already
drifted off the query), so this runs on requests alone: no Chrome, no scroll.

Usage:
    python3 fairprice_search_crawler.py                     # every term in the CSV
    python3 fairprice_search_crawler.py --min-rows 20       # only the frequent ones
    python3 fairprice_search_crawler.py --term sandwich --term cereals
    python3 fairprice_search_crawler.py --resume            # keep what is already out
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import requests

from fairprice_crawler import USER_AGENT, dedupe, parse_products

SEARCH_URL = "https://www.fairprice.com.sg/search?query={}"

# term/occurrences carried through so a row still says which unmatched food it
# was fetched for, and how much of the gap that food accounts for
FIELDS = ["term", "occurrences", "rank", "product_id", "name", "price_value",
          "quantity", "dietary"]


def read_terms(path: str, min_rows: int) -> list[tuple[str, int]]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [
            (r["name"].strip(), int(r["occurrences"]))
            for r in csv.DictReader(fh)
        ]
    return [(name, n) for name, n in rows if name and n >= min_rows]


def search(term: str, session: requests.Session, timeout: int, retries: int) -> str:
    url = SEARCH_URL.format(quote_plus(term))
    last = None
    for attempt in range(retries + 1):
        try:
            r = session.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-SG,en;q=0.9",
                },
                timeout=timeout,
            )
            r.raise_for_status()
            return r.text
        except Exception as exc:  # transient 5xx / timeout: back off and retry
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--terms-csv", default="data/unmatched_food.csv",
                    help="input: the name/occurrences table (default: %(default)s)")
    ap.add_argument("--term", action="append", default=None,
                    help="search this term instead of reading the CSV (repeatable)")
    ap.add_argument("--min-rows", type=int, default=0,
                    help="skip terms accounting for fewer than N unmatched rows")
    ap.add_argument("--out", default="data/unmatched_food_prices.csv")
    ap.add_argument("--top", type=int, default=0,
                    help="keep only the first N results per term (0 = all)")
    ap.add_argument("--jobs", type=int, default=6, help="concurrent searches")
    ap.add_argument("--delay", type=float, default=0.35,
                    help="pause between requests within a worker")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--resume", action="store_true",
                    help="append, skipping terms already present in --out")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    verbose = not args.quiet

    if args.term:
        terms = [(t, 0) for t in args.term]
    else:
        terms = read_terms(args.terms_csv, args.min_rows)

    done: set[str] = set()
    if args.resume and os.path.exists(args.out):
        with open(args.out, newline="", encoding="utf-8") as fh:
            done = {r["term"] for r in csv.DictReader(fh)}
        terms = [(t, n) for t, n in terms if t not in done]
        if verbose:
            print(f"resuming: {len(done)} terms already crawled, {len(terms)} left",
                  file=sys.stderr)

    if not terms:
        print("nothing to crawl", file=sys.stderr)
        return 0

    append = args.resume and done
    fh = open(args.out, "a" if append else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    if not append:
        writer.writeheader()

    # one lock for the shared file: rows are written as each term lands, so an
    # interrupted run keeps everything crawled up to that point
    lock = threading.Lock()
    local = threading.local()
    counts = {"terms": 0, "rows": 0, "empty": 0, "failed": 0}

    def crawl(job: tuple[str, int]) -> None:
        term, occurrences = job
        session = getattr(local, "session", None)
        if session is None:
            session = local.session = requests.Session()

        try:
            html = search(term, session, args.timeout, args.retries)
        except Exception as exc:
            with lock:
                counts["failed"] += 1
            print(f"[{term}] FAILED: {exc}", file=sys.stderr)
            return

        products = dedupe(parse_products(html, term))
        if args.top:
            products = products[: args.top]

        with lock:
            for rank, p in enumerate(products, start=1):
                writer.writerow({
                    "term": term,
                    "occurrences": occurrences,
                    "rank": rank,
                    "product_id": p.product_id,
                    "name": p.name,
                    "price_value": p.price_value,
                    "quantity": p.quantity,
                    "dietary": p.dietary,
                })
            fh.flush()
            counts["terms"] += 1
            counts["rows"] += len(products)
            if not products:
                counts["empty"] += 1
            if verbose and counts["terms"] % 25 == 0:
                print(f"  {counts['terms']}/{len(terms)} terms, "
                      f"{counts['rows']} rows", file=sys.stderr)

        time.sleep(args.delay)

    if verbose:
        print(f"searching {len(terms)} terms across {args.jobs} workers -> {args.out}",
              file=sys.stderr)

    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(crawl, terms))
    except KeyboardInterrupt:
        print("interrupted; keeping what was written", file=sys.stderr)
    finally:
        fh.close()

    if verbose:
        print(f"\n{counts['rows']} listings for {counts['terms']} terms -> {args.out}")
        print(f"terms with no result: {counts['empty']}; failed: {counts['failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
