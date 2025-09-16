# Debian Contents Package Extrator

This is a Python CLI tool to fetch Debian **Contents** index for the specified architecture and print **top N packages with the highest number of files**.

Mirror used by default: `http://ftp.uk.debian.org/debian/dists/stable/main/`
However, this can be changed by parsing another mirror using **--mirror** arg.

---

## How it works

- Builds the expected Contents file URL for the given architecture: `Contents-<arch>.gz` (falls back to `Contents-<arch>.xz`).
- Streams and decompresses the file from the Debian mirror using Python **standard libraries** (`urllib`, `gzip`, `lzma`).
- Parses each line (`<path> <packages>`) and counts one file for **each package** listed on that line 
    Note: The **Contents format** is documented by Debian: https://wiki.debian.org/RepositoryFormat#A.22Contents.22_indices
- Sorts the packages by descending file count and prints the top `N` packages with highest file count in a tabular form.

---

## Dependencies

Tested with Python 3.11. Clone or extract this repository locally.
No dependency is beyong Python 3.9

---

## Usage

```bash
./package_extraction.py amd64
```

Options:
```bash
--mirror    Debian mirror base (default: http://ftp.uk.debian.org/debian)
--suite     Suite / release (default: stable)
--component Component (default: main)
--top       Number of rows to print (default: 10)
-v / -vv    Verbose / debug logging
```

Examples:
```bash
./package_extraction.py amd64
./package_extraction.py arm64 --top 20
./package_extraction.py mipsel --mirror http://ftp.uk.debian.org/debian --suite stable --component main
```

---

## Design Approach (Thought Process)

- **Get to know with the documentation:** Followed Debian’s documented Contents format. Lines have two columns: a file path and a comma‑separated list of packages. 
- **Thought process for file fetching:** Eventhough the ``Contents`` index has only `.gz` extension, there were ``.xz`` files in the mirror, so thought to try `.gz` first and if that doesn't work, then `.xz`. Also it should be able to handle HTTP requests errors correctly.
- **Consideration of memory usage:** Used the network stream directly with `gzip.GzipFile` / `lzma.LZMAFile` wrapped by `TextIOWrapper` to avoid the need to store the whole file locally.
- **CLI ergonomics:** Added `--mirror`, `--suite`, `--component`, `--top`, and verbosity flags.
- **Readability:** Type hints, modularity, and explicit `logging` for diagnostics.

---

## Testing

- **Unit parsing test:** I manually verified `parse_contents_lines` on a tiny synthetic snippet for tricky cases (multiple packages; odd whitespace; blank lines) to verify the functionality
- **End‑to‑end testing:** Verified with the UK Debian mirror for `amd64`, `arm64`, and `mipsel` to ensure everything is working fine and also compared the results manually.

---

## Time spent

 Approximately 2 hours including reading Debian docs, coding, improving CLI, and writing this README.

