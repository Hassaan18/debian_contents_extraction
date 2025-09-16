"""

This python tool downloads Debian's "Contents" index for the specified architecture 
and extracts the top N packages with the most files associated.

It first tries to download the .gz version of the Contents file, and if that fails, it tries the .xz version.

Default mirror: http://ftp.uk.debian.org/debian/dists/stable/main/

Usage:
    ./package_extraction.py amd64 --top 10 --mirror http://ftp.uk.debian.org/debian --suite stable --component main

"""

import argparse
import gzip
import io
import logging
import lzma
import sys
import textwrap
import urllib.error
import urllib.request
from collections import Counter
from typing import Iterable, Tuple, Optional

AGENT = "Hassaan"

DEFAULT_MIRROR = "http://ftp.uk.debian.org/debian"
DEFAULT_SUITE = "stable"
DEFAULT_COMPONENT = "main"

def build_contents_urls(
    arch: str,
    mirror: str = DEFAULT_MIRROR,
    suite: str = DEFAULT_SUITE,
    component: str = DEFAULT_COMPONENT,
) -> Tuple[str, str]:
    """
    Generates and returns the debian package link (for both .gz and .xz) for the specified architecture
    """
    base = f"{mirror.rstrip('/')}/dists/{suite}/{component}"
    gz = f"{base}/Contents-{arch}.gz"
    xz = f"{base}/Contents-{arch}.xz"
    return gz, xz

def try_open_url(url: str) -> Optional[io.BufferedReader]:
    """
    Opens and check if the file is available at the generated URL.
    If not, gives the file not found error or HTTP error incase of other issues.
    """
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        resp = urllib.request.urlopen(req)
        return resp 
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logging.debug("URL not found (404): %s", url)
            return None
        logging.error("HTTP error fetching %s: %s", url, e)
        return None
    except urllib.error.URLError as e:
        logging.error("Network error fetching %s: %s", url, e)
        return None

def open_remote_contents_stream(arch: str, mirror: str, suite: str, component: str) -> Tuple[Iterable[str], str]:
    """
    Opens the remote contents file for the specified architecture and return the text line iterator and url used
    This first tries to open the .gz file, and if that fails, it tries the .xz file.
    If both fail, it raises a RuntimeError.
    """
    gz_url, xz_url = build_contents_urls(arch, mirror, suite, component)

    resp = try_open_url(gz_url)
    if resp is not None:
        gz_stream = gzip.GzipFile(fileobj=resp)  # wrap response in gzip stream reader
        text_stream = io.TextIOWrapper(gz_stream, encoding="utf-8", errors="replace")
        return text_stream, gz_url

    resp = try_open_url(xz_url) # If the gz doesn't work
    if resp is not None:
        xz_stream = lzma.LZMAFile(resp)
        text_stream = io.TextIOWrapper(xz_stream, encoding="utf-8", errors="replace")
        return text_stream, xz_url

    raise RuntimeError(
        f"Could not find Contents file for '{arch}'. Tried:\n  {gz_url}\n  {xz_url}"
    )

def parse_contents_lines(lines: Iterable[str]) -> Counter:
    """
    Parse the lines from the debian contents file and also counts the file count for each package
    Since the format is defined as:
        <path> <package1,...,packageN>
    The function
        split on whitespace from the right, to separate the final "packages" column
        split the packages field on commas
        increment each package's count by 1 (one file per line)
    """
    counts: Counter[str] = Counter()
    for data in lines:
        line = data.strip()
        if not line or line.startswith("#"):
            continue
        try:
            pkg_field = line.rsplit(None, 1)[1]
        except (ValueError, IndexError):
            logging.debug("Skipping unstructured line: %r", line)
            continue
        pkgs = [pkg.strip() for pkg in pkg_field.split(",") if pkg.strip()]
        counts.update(pkgs)
    return counts

def top_n_packages(counts: Counter, n: int) -> list[Tuple[str, int]]:
    """
    Return the top-N packages in the descending file count order
    """
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]

def format_table(rows: Iterable[Tuple[str, int]]) -> str:
    """
    Format the data into a tabular form  i.e., Package, File Count
    """
    rows = list(rows)
    if not rows:
        return "(no data)"
    name_width = max(len(name) for name, _ in rows)
    count_width = max(len(str(cnt)) for _, cnt in rows)
    lines = []
    lines.append(f"\n{'Package'.ljust(30)}  {'File Count'.rjust(20)}")
    lines.append(f"{'-' * name_width}{'------------'}")
    for name, cnt in rows:
        lines.append(f"{name.ljust(name_width)}  {str(cnt).rjust(count_width)}")
    return "\n".join(lines) + "\n"

def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Reads and fetches the argument from the command line. If not found, uses the default arguments
    """
    parser = argparse.ArgumentParser(
        description="Show top packages by file count from Debian Mirror",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            f"""\
            Function call expamples:
                package_extraction.py amd64
                package_extraction.py arm64 --top 20
                package_extraction.py mipsel --mirror {DEFAULT_MIRROR} --suite stable --component main
            """
        ),
    )
    arg_dict = [
        # dict(args=("arch",), kwargs={"nargs":'?', "default":'amd64'}),  # For testing purposes  directly from 
        dict(args=("arch",), kwargs={"help":"Architecture (e.g., amd64, arm64, mipsel)"}),
        dict(args=("--mirror",), kwargs={"default":DEFAULT_MIRROR, "help":f"Debian mirror base URL (default: {DEFAULT_MIRROR})"}),
        dict(args=("--suite",), kwargs={"default":DEFAULT_SUITE, "help":f"Suite/release (default: {DEFAULT_SUITE})"}),
        dict(args=("--component",), kwargs={"default":DEFAULT_COMPONENT, "help":f"Component (default: {DEFAULT_COMPONENT})"}),
        dict(args=("--top",), kwargs={"type":int, "default":10, "help":"Number of top packages to display (default: 10)"}),
        dict(args=("-v", "--verbose"), kwargs={"action":"count", "default":0, "help":"Increase verbosity (-v, -vv)"}),
    ]
    for arg in arg_dict:
        parser.add_argument(*arg["args"], **arg["kwargs"])
    return parser.parse_args(argv)

def configure_logging(verbosity: int) -> None:
    """
    Configure logging based on verbosity level. Default is set to Warning.
    """
    level = logging.WARNING 
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

if __name__ == "__main__":
    import sys
    args = parse_args(sys.argv[1:])
    configure_logging(args.verbose)

    try:
        stream, source = open_remote_contents_stream(args.arch, args.mirror, args.suite, args.component)
        logging.info("Reading Contents from: %s", source)
        counts = parse_contents_lines(stream)
        rows = top_n_packages(counts, args.top)
        print(format_table(rows))
        sys.exit(0)
    except Exception as excp_err:
        logging.error("%s", excp_err)
        sys.exit(1)
