"""The audit-PDF and proposal surfaces stay removed.

`generate_pdf_report.py` was a second renderer of the same report
contract `geo-report` renders in markdown. Keeping both meant
implementing every contract change twice, and the duplication shipped a
crash to clients in v0.4.3 — a finding quoting `<link rel=canonical>`
aborted PDF generation outright.

`geo-proposal` was a sales-proposal generator carried over from the
upstream library. The project's focus is the GEO report as the main
deliverable, for technically savvy site owners and SEO/GEO developers.

This guard exists because the references were spread across 15+ files. A
partial revert would leave the skills advertising commands that no
longer exist, which is worse than either keeping or removing them.
"""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files scanned for dangling references to the removed surfaces.
SCANNED = (
    "README.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "install.sh",
    "install-win.sh",
    "requirements.txt",
    "evals/report-contract-scenarios.md",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "skills/geo/SKILL.md",
    "skills/geo-audit/SKILL.md",
    "skills/geo-compare/SKILL.md",
    "skills/geo-prospect/SKILL.md",
    "skills/geo-reporter-setup/SKILL.md",
    "skills/geo-report/SKILL.md",
)

# Naming the removed surfaces. "PDF" alone is deliberately NOT a
# pattern: geo-audit legitimately says it skips PDFs as crawl input.
# "proposal" alone is likewise allowed: the CRM (geo-prospect,
# crm_dashboard, webapp) tracks a proposal_file as data regardless of
# what wrote the file.
FORBIDDEN = (
    re.compile(r"generate_pdf_report"),
    re.compile(r"report-pdf"),
    re.compile(r"reportlab", re.IGNORECASE),
    re.compile(r"geo-proposal"),
    re.compile(r"/geo proposal"),
)


def _read(rel):
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TestRemovedFilesStayRemoved:
    def test_pdf_generator_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "scripts", "generate_pdf_report.py"))

    def test_pdf_skill_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "skills", "geo-report-pdf"))

    def test_pdf_tests_are_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "tests", "test_pdf_tldr.py"))

    def test_proposal_skill_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "skills", "geo-proposal"))


class TestNoDanglingReferences:
    def test_no_file_names_the_removed_surfaces(self):
        offenders = []
        for rel in SCANNED:
            content = _read(rel)
            if content is None:
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                for pattern in FORBIDDEN:
                    if pattern.search(line):
                        offenders.append(f"{rel}:{line_no}: {line.strip()}")
        assert not offenders, (
            "these still advertise a command that no longer exists:\n"
            + "\n".join(offenders)
        )

    def test_reportlab_is_not_a_dependency(self):
        assert "reportlab" not in (_read("requirements.txt") or "").lower()


class TestUnrelatedMentionsSurvive:
    """Neither "PDF" nor "proposal" is forbidden as a plain word.

    geo-audit tells the crawler to skip PDFs as input, and the CRM
    legitimately tracks a proposal pipeline status. Scrubbing those
    while removing the generators would change behaviour this release
    is not about.
    """

    def test_geo_audit_still_skips_pdf_input(self):
        content = _read("skills/geo-audit/SKILL.md") or ""
        assert "Skip PDFs" in content

    def test_crm_still_tracks_proposal_status(self):
        content = _read("skills/geo-prospect/SKILL.md") or ""
        assert "proposal" in content.lower()
