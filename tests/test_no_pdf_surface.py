"""The audit-PDF and proposal surfaces stay removed.

`generate_pdf_report.py` was a second renderer of the same report
contract `geo-report` renders in markdown. Keeping both meant
implementing every contract change twice, and the duplication shipped a
crash to clients in v0.4.3 — a finding quoting `<link rel=canonical>`
aborted PDF generation outright.

`geo-proposal` was a sales-proposal generator and `geo-prospect` (with
`crm_dashboard.py` and the Flask webapp) a CRM-lite sales pipeline, both
carried over from the upstream library. The project's focus is the GEO
report as the main deliverable, for technically savvy site owners and
SEO/GEO developers. `geo-compare` (delta reports between audit runs)
stays — it serves the report, not the pipeline.

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
    "uninstall.sh",
    "skills/geo/SKILL.md",
    "skills/geo/REPORT-CONTRACT.md",
    "skills/geo-audit/SKILL.md",
    "skills/geo-compare/SKILL.md",
    "skills/geo-reporter-setup/SKILL.md",
    "skills/geo-report/SKILL.md",
)

# Naming the removed surfaces. "PDF" alone is deliberately NOT a
# pattern: geo-audit legitimately says it skips PDFs as crawl input.
# "proposal" and "prospect" alone are likewise allowed: the report
# contract's rule 13 legitimately talks about auditing a prospect's
# site, and `~/.geo-prospects/` remains geo-compare's data directory
# (note the \b — "geo-prospect" must not match "geo-prospects").
FORBIDDEN = (
    re.compile(r"generate_pdf_report"),
    re.compile(r"report-pdf"),
    re.compile(r"reportlab", re.IGNORECASE),
    re.compile(r"geo-proposal"),
    re.compile(r"/geo proposal"),
    re.compile(r"geo-prospect\b"),
    re.compile(r"/geo prospect"),
    re.compile(r"crm_dashboard"),
    re.compile(r"scripts/webapp"),
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

    def test_prospect_skill_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "skills", "geo-prospect"))

    def test_crm_dashboard_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "scripts", "crm_dashboard.py"))

    def test_webapp_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "scripts", "webapp"))

    def test_demo_prospects_data_is_gone(self):
        assert not os.path.exists(
            os.path.join(REPO, "examples", "prospects-demo.json"))


class TestNoDanglingReferences:
    def test_no_file_names_the_removed_surfaces(self):
        offenders = []
        for rel in SCANNED:
            content = _read(rel)
            if content is None:
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                # The install scripts' prune list and the uninstaller's
                # removal list must name the retired skills in order to
                # delete them — the only places naming the surface is
                # the fix, not a dangling reference.
                if "RETIRED_SKILLS" in line or "GEO_REPORTER_SKILLS" in line:
                    continue
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

    def test_report_contract_still_covers_prospect_sites(self):
        """Rule 13's external-mode guidance uses "prospect" as a plain
        word — a site being audited before engagement — and must not be
        scrubbed along with the CRM skill."""
        content = _read("skills/geo/REPORT-CONTRACT.md") or ""
        assert "prospect" in content.lower()

    def test_geo_compare_survives(self):
        """Delta reports serve the report, not the sales pipeline."""
        assert os.path.exists(
            os.path.join(REPO, "skills", "geo-compare", "SKILL.md"))


class TestUninstallerListsStayInSync:
    """uninstall.sh removes only GEO Reporter's own skills and agents, by
    explicit name — a bare geo-*/ glob would also delete user-authored
    skills sharing the prefix (a real geo-observe nearly went this way).

    The cost of explicit lists is drift, so this pins them to the repo:
    every shipped skill/agent must be in the list (or uninstall leaves
    it behind), and everything else in the list must be a known retired
    name (or uninstall would delete something that was never ours).
    """

    RETIRED = {"geo-report-pdf", "geo-proposal", "geo-prospect"}

    def _list_from_uninstall(self, var):
        content = _read("uninstall.sh") or ""
        match = re.search(rf'{var}="([^"]+)"', content)
        assert match, f"{var} not found in uninstall.sh"
        return set(match.group(1).split())

    def test_skill_list_matches_shipped_plus_retired(self):
        shipped = {
            name for name in os.listdir(os.path.join(REPO, "skills"))
            if name.startswith("geo-")
        }
        listed = self._list_from_uninstall("GEO_REPORTER_SKILLS")
        assert listed == shipped | self.RETIRED, (
            f"missing from uninstall.sh: {sorted((shipped | self.RETIRED) - listed)}; "
            f"unknown in uninstall.sh: {sorted(listed - shipped - self.RETIRED)}"
        )

    def test_agent_list_matches_shipped(self):
        shipped = {
            name[:-3] for name in os.listdir(os.path.join(REPO, "agents"))
            if name.endswith(".md")
        }
        listed = self._list_from_uninstall("GEO_REPORTER_AGENTS")
        assert listed == shipped
