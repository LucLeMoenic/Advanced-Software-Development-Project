"""Render a pytest JUnit XML file as a Markdown table for the GitHub job summary.

Usage: python scripts/test/junit_summary.py <junit.xml> "<title>"
Appends to $GITHUB_STEP_SUMMARY when set, otherwise prints to stdout. Exits
non-zero if the XML is missing or contains failures/errors, so a broken report
can never look green.
"""

import os
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parses our own pytest output, not untrusted input


def main(path: str, title: str) -> int:
    try:
        root = ET.parse(path).getroot()  # noqa: S314 - same: trusted CI-generated file
    except (OSError, ET.ParseError) as exc:
        print(f"Cannot read {path}: {exc}")
        return 1
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    cases = [c for s in suites for c in s.findall("testcase")]
    lines = [f"### {title}", "", "| Test | Result |", "|---|---|"]
    bad = 0
    for case in cases:
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        bad += failed
        verdict = "FAIL" if failed else ("skipped" if skipped else "pass")
        lines.append(f"| `{case.get('classname', '').split('.')[-1]}::{case.get('name')}` | {verdict} |")
    lines += ["", f"**{len(cases) - bad} of {len(cases)} passed**", ""]
    text = "\n".join(lines)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 1 if bad or not cases else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Test results"))
