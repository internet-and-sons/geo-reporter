#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# GEO Reporter — Claude Code Skill Uninstaller
# ============================================================

CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
AGENTS_DIR="${CLAUDE_DIR}/agents"

# Detect if running via curl pipe (no interactive input available)
INTERACTIVE=true
if [ ! -t 0 ]; then
    INTERACTIVE=false
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure unmatched globs expand to nothing
shopt -s nullglob

# Skills that belong to GEO Reporter — current and retired. Only these
# are removed. A bare geo-*/ glob would also delete user-authored skills
# that happen to share the prefix (e.g. a private geo-observe), which
# install.sh and dev-unlink.sh deliberately preserve.
# Kept in sync with skills/ by tests/test_no_pdf_surface.py.
GEO_REPORTER_AGENTS="geo-ai-visibility geo-content geo-platform-analysis geo-schema geo-technical"
GEO_REPORTER_SKILLS="geo-agentready geo-audit geo-botaccess geo-brand-mentions geo-citability geo-compare geo-content geo-crawlers geo-integrity geo-llmstxt geo-platform-optimizer geo-report geo-reporter-setup geo-schema geo-technical geo-report-pdf geo-proposal geo-prospect"

echo ""
echo -e "${YELLOW}GEO Reporter — Claude Code Skill Uninstaller${NC}"
echo ""
echo "This will remove the following:"
echo ""

# List what will be removed
[ -d "$SKILLS_DIR/geo" ] && echo "  → ${SKILLS_DIR}/geo/"
for skill_name in $GEO_REPORTER_SKILLS; do
    [ -d "$SKILLS_DIR/$skill_name" ] && echo "  → ${SKILLS_DIR}/${skill_name}/"
done
for agent_name in $GEO_REPORTER_AGENTS; do
    [ -f "$AGENTS_DIR/$agent_name.md" ] && echo "  → ${AGENTS_DIR}/${agent_name}.md"
done

echo ""
if [ "$INTERACTIVE" = true ]; then
    read -p "Are you sure you want to uninstall? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled."
        exit 0
    fi
else
    echo -e "${YELLOW}Non-interactive mode — proceeding with uninstall...${NC}"
fi

echo ""

# Remove main skill
if [ -d "$SKILLS_DIR/geo" ]; then
    rm -rf "$SKILLS_DIR/geo"
    echo -e "${GREEN}✓ Removed main skill${NC}"
fi

# Remove sub-skills — only GEO Reporter's own; user skills sharing the
# geo- prefix are left alone.
for skill_name in $GEO_REPORTER_SKILLS; do
    if [ -d "$SKILLS_DIR/$skill_name" ]; then
        rm -rf "${SKILLS_DIR:?}/${skill_name}"
        echo -e "${GREEN}✓ Removed ${skill_name}${NC}"
    fi
done

# Remove agents — only GEO Reporter's own, by name.
for agent_name in $GEO_REPORTER_AGENTS; do
    if [ -f "$AGENTS_DIR/$agent_name.md" ]; then
        rm -f "$AGENTS_DIR/$agent_name.md"
        echo -e "${GREEN}✓ Removed ${agent_name}.md${NC}"
    fi
done

echo ""
echo -e "${GREEN}GEO Reporter has been uninstalled.${NC}"
echo ""
echo "Note: Python dependencies were not removed."
echo "To remove them manually:"
echo "  pip uninstall beautifulsoup4 requests lxml playwright urllib3"
echo ""
echo "Note: Runtime data at ~/.geo-prospects/ (saved audits, delta reports) was not removed."
echo "To remove it manually:"
echo "  rm -rf ~/.geo-prospects"
echo ""
