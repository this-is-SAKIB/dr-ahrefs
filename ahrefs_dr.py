#!/usr/bin/env python3
"""Bulk Ahrefs Domain Rating checker.

Standard library only. Reads one target per line, or the selected column from
a CSV/TSV file, and writes a table-shaped CSV result.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://api.ahrefs.com/v3/public/domain-rating-free?output=json"
MAX_TARGETS = 1000
MAX_RETRIES = 3
RETRY_DELAYS = (5, 15, 30)


class ApiFailure(RuntimeError):
    """An Ahrefs API request failed after any allowed retries."""


def clean_target(value: str) -> str:
    target = str(value or "").strip()
    if len(target) >= 2 and target[0] == target[-1] and target[0] in {"\"", "'"}:
        target = target[1:-1].strip()
    if not target or any(char.isspace() for char in target):
        return ""
    return target


def target_key(value: str) -> str:
    key = clean_target(value).lower()
    if key.startswith("https://"):
        key = key[8:]
    elif key.startswith("http://"):
        key = key[7:]
    return key.rstrip("/")


def looks_like_header(value: str) -> bool:
    return clean_target(value).lower() in {
        "url", "urls", "domain", "domains", "target", "targets", "website", "websites"
    }


def read_targets(path: str, column: int) -> List[Tuple[int, str]]:
    """Return (source row, raw value) pairs. Column numbers are 1-based."""
    if path == "-":
        text = sys.stdin.read()
        source_name = "stdin"
    else:
        source_name = path
        text = Path(path).read_text(encoding="utf-8-sig")

    if not text.strip():
        return []

    suffix = Path(source_name).suffix.lower()
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    is_tabular = suffix in {".csv", ".tsv"} or "\t" in first_line or "," in first_line

    if not is_tabular:
        values = [(index, line) for index, line in enumerate(text.splitlines(), start=1)]
    else:
        delimiter = "\t" if suffix == ".tsv" or "\t" in first_line else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        values = []
        for index, row in enumerate(reader, start=1):
            if not row:
                values.append((index, ""))
                continue
            values.append((index, row[column - 1] if len(row) >= column else ""))

    if values and looks_like_header(values[0][1]):
        values = values[1:]
    return values


def api_error_message(status: int, body: str) -> str:
    detail = ""
    try:
        payload = json.loads(body or "{}")
        error = payload.get("error") or payload.get("message")
        detail = error if isinstance(error, str) else json.dumps(error) if error else ""
    except json.JSONDecodeError:
        detail = " ".join((body or "").split())[:300]
    return f"HTTP {status}" + (f": {detail}" if detail else "")


def request_ratings(targets: List[str], api_key: str, version: str) -> Dict[str, dict]:
    payload = json.dumps({"targets": targets, "version": version}).encode("utf-8")
    last_error = "Unknown Ahrefs API error"

    for attempt in range(MAX_RETRIES + 1):
        request = Request(
            ENDPOINT,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ahrefs-dr-checker/1.0",
            },
        )
        try:
            with urlopen(request, timeout=90) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            status = error.code
            body = error.read().decode("utf-8", errors="replace")
        except URLError as error:
            raise ApiFailure(f"Network error: {error.reason}") from error
        except TimeoutError as error:
            raise ApiFailure("Request timed out") from error

        if 200 <= status < 300:
            try:
                payload_json = json.loads(body or "{}")
            except json.JSONDecodeError as error:
                raise ApiFailure("Ahrefs returned invalid JSON") from error
            outer = payload_json.get("domain_rating", payload_json)
            ratings = {}
            for item in outer.get("targets", []):
                returned_target = clean_target(item.get("target", ""))
                if returned_target:
                    ratings[target_key(returned_target)] = {
                        "target": returned_target,
                        "domain_rating": item.get("domain_rating", ""),
                    }
            return ratings

        last_error = api_error_message(status, body)
        if status != 429 or attempt == MAX_RETRIES:
            break
        delay = RETRY_DELAYS[attempt]
        print(f"Ahrefs returned HTTP 429; retrying in {delay}s…", file=sys.stderr)
        time.sleep(delay)

    raise ApiFailure(last_error)


def build_records(source_values: Iterable[Tuple[int, str]]) -> Tuple[List[dict], List[dict]]:
    records = []
    unique_jobs = []
    seen = set()

    for source_row, raw_value in source_values:
        input_value = str(raw_value or "").strip()
        target = clean_target(input_value)
        if not input_value:
            continue

        record = {
            "source_row": source_row,
            "input": input_value,
            "target": target,
            "key": target_key(target) if target else "",
            "status": "",
            "domain_rating": "",
            "checked_at": "",
            "ahrefs_target": target,
            "error": "",
        }
        if not target:
            record["status"] = "INVALID"
            record["error"] = "Remove spaces and enter one domain or URL per row."
        elif record["key"] in seen:
            record["status"] = "DUPLICATE"
        else:
            seen.add(record["key"])
            unique_jobs.append(record)
        records.append(record)

    return records, unique_jobs


def run(args: argparse.Namespace) -> int:
    api_key = args.api_key or os.environ.get("AHREFS_API_KEY", "").strip()
    if not api_key:
        if not sys.stdin.isatty():
            print("Set AHREFS_API_KEY or use --api-key; refusing to read a key from piped input.", file=sys.stderr)
            return 2
        api_key = getpass.getpass("Ahrefs API key: ").strip()
    if not api_key:
        print("No API key supplied.", file=sys.stderr)
        return 2

    try:
        source_values = read_targets(args.input, args.column)
    except OSError as error:
        print(f"Could not read input: {error}", file=sys.stderr)
        return 2

    records, unique_jobs = build_records(source_values)
    if not records:
        print("No non-empty targets found.", file=sys.stderr)
        return 2

    checked_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    api_calls = 0
    for offset in range(0, len(unique_jobs), MAX_TARGETS):
        chunk = unique_jobs[offset : offset + MAX_TARGETS]
        print(f"Checking {offset + 1}-{offset + len(chunk)} of {len(unique_jobs)} unique target(s)…")
        try:
            ratings = request_ratings([job["target"] for job in chunk], api_key, args.version)
            api_calls += 1
        except ApiFailure as error:
            api_calls += 1
            message = str(error)
            for job in chunk:
                job["status"] = "RATE LIMITED" if "HTTP 429" in message else "ERROR"
                job["error"] = message
            continue

        for job in chunk:
            rating = ratings.get(job["key"])
            if rating is None:
                job["status"] = "ERROR"
                job["error"] = "Ahrefs returned no result for this target."
            else:
                job["status"] = "OK"
                job["domain_rating"] = rating.get("domain_rating", "")
                job["ahrefs_target"] = rating.get("target", job["target"])

    for record in records:
        if record["status"] == "DUPLICATE":
            source = next((item for item in unique_jobs if item["key"] == record["key"]), None)
            if source:
                record["domain_rating"] = source["domain_rating"]
                record["ahrefs_target"] = source["ahrefs_target"]
                if source["status"] != "OK":
                    record["status"] = source["status"]
                    record["error"] = source["error"]
        if record["status"] in {"OK", "DUPLICATE", "ERROR", "RATE LIMITED"}:
            record["checked_at"] = checked_at

    output_path = Path(args.output)
    try:
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "Input Row", "Input", "Normalized Target", "Status",
                    "Domain Rating", "Checked At (UTC)", "Ahrefs Target", "Error",
                ],
            )
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "Input Row": record["source_row"],
                    "Input": record["input"],
                    "Normalized Target": record["target"],
                    "Status": record["status"],
                    "Domain Rating": record["domain_rating"],
                    "Checked At (UTC)": record["checked_at"],
                    "Ahrefs Target": record["ahrefs_target"],
                    "Error": record["error"],
                })
    except OSError as error:
        print(f"Could not write output: {error}", file=sys.stderr)
        return 2

    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    print(f"Wrote {len(records)} row(s) to {output_path} using {api_calls} API request(s): {summary}")
    print("Attribution: Domain Rating by Ahrefs — https://ahrefs.com/")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk-check Ahrefs Domain Rating for domains or URLs.")
    parser.add_argument("input", help="Input .txt, .csv, or .tsv file; use - to read targets from stdin.")
    parser.add_argument("-o", "--output", default="ahrefs_dr_results.csv", help="Output CSV path (default: ahrefs_dr_results.csv).")
    parser.add_argument("--column", type=int, default=1, help="1-based CSV/TSV column to read (default: 1).")
    parser.add_argument("--version", choices=("dr3", "dr4"), default="dr3", help="Ahrefs DR version (default: dr3).")
    parser.add_argument("--api-key", help="API key; preferably use AHREFS_API_KEY or the secure prompt instead.")
    return parser


if __name__ == "__main__":
    arguments = make_parser().parse_args()
    if arguments.column < 1:
        print("--column must be 1 or greater.", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(run(arguments))
