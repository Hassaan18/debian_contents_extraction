# This is just a test file to verify the fucntionality of package_statistics.py

from package_extraction import parse_contents_lines, top_n_packages

stream = """
usr/bin/foo pkg-foo
usr/share/doc/bar pkg-bar,pkg-baz,pkg-foo
/var/lib/thing pkg-baz
usr/bin/qux pkg-qux
user/bin/foo3 pkg-foo
usr/share/doc/bar2 pkg-bar,pkg-baz,pkg-foo
/var/lib/thing2 pkg-baz
"""

counts = parse_contents_lines(stream.splitlines())
print("Counted:", counts)
print("Top Counts:", top_n_packages(counts, 3))
