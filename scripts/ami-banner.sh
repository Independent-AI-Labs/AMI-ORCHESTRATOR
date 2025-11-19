#!/usr/bin/env bash
# AMI Orchestrator Banner and Color Functions
#
# This script contains color definitions and banner display functions
# for the AMI Orchestrator system. It provides consistent color output
# and banner display across all scripts.

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[38;5;203m'
PURPLE='\033[38;5;99m'
CYAN='\033[0;36m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

# Define quiet mode echo function
_ami_echo() {
    if [[ "$AMI_QUIET_MODE" != "1" ]]; then
        echo -e "$@"
    fi
}

# Function to display the banner
display_banner() {
    _ami_echo "${GREEN}✓${NC} AMI Orchestrator shell environment configured successfully!"
    _ami_echo ""
    _ami_echo " __      ___                         _     __  __  ___ "
    _ami_echo " \ \    / _ \  _ __   ___  _ __     / \   |  \/  ||_ _|        __   ___ "
    _ami_echo "  \ \  | | | || '_ \ / _ \| '_ \   / _ \  | |\/| | | |   __ __/  \ |_  )"
    _ami_echo "  / /  | |_| || |_) |  __/| | | | / ___ \ | |  | | | |   \ V / () | / / "
    _ami_echo " /_/    \___/ | .__/ \___||_| |_|/_/   \_\|_|  |_||___|   \_/ \__(_)___|"
    _ami_echo "              |_|"
    _ami_echo ""
    _ami_echo "${GREEN}> Secure infrastructure for distributed enterprise automation and governance."
    _ami_echo "> Supports bare metal, cloud, and hybrid deployments with 0 vendor lock-in."
    _ami_echo "> Safely integrates with any local or remote web, data, and API service."
    _ami_echo "${RED}"
    _ami_echo "============================================================================="
    _ami_echo "> Transparent and auditable open-source project by Indepentent AI Labs."
    _ami_echo "> Full NIST AI CSF/RMF, ISO 42001/27001, and EU AI Act compliance."
    _ami_echo "============================================================================="
    _ami_echo "${NC}"
    _ami_echo "${RED}🔴 Core Execution & Management:${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-run${NC}       → Sandboxed universal execution wrapper${NC}"
    _ami_echo "                    ${GREEN}uv, python, node, npm, npx, java, php; ${NC}virtualisation:"
    _ami_echo "                    ${GREEN}kvm (qemu), hyperv, podman, wine (proton), android${NC}"
    _ami_echo "  ${RED}> ami-agent${NC}     → AI agent orchestration and automation${NC}"
    _ami_echo "                    ${GREEN}interactive${NC}, ${GREEN}continue${NC}, ${GREEN}resume${NC}, ${GREEN}print${NC}, ${GREEN}hook${NC}, ${GREEN}audit${NC}, ${GREEN}tasks${NC},"
    _ami_echo "                    ${GREEN}sync${NC}, ${GREEN}docs${NC}"
    _ami_echo "  ${RED}> ami-repo${NC}      → Git repository server management${NC}"
    _ami_echo "                    ${GREEN}init${NC}, ${GREEN}create${NC}, ${GREEN}list${NC}, ${GREEN}url${NC}, ${GREEN}clone${NC}, ${GREEN}delete${NC}, ${GREEN}info${NC}, ${GREEN}add-key${NC},"
    _ami_echo "                    ${GREEN}list-keys${NC}, ${GREEN}remove-key${NC}, ${GREEN}generate-key${NC}, ${GREEN}service${NC}"
    _ami_echo "  ${RED}> ami-services${NC}  → Service orchestration${NC}"
    _ami_echo "                    ${GREEN}start${NC}, ${GREEN}stop${NC}, ${GREEN}restart${NC}, ${GREEN}profile${NC}, ${GREEN}status${NC}"
    _ami_echo ""
    _ami_echo "${PURPLE}🟣 Module-Specific Development Tools:${NC}"
    _ami_echo ""
    _ami_echo "  ${PURPLE}> ami-test${NC}      → Run tests from any directory${NC}"
    _ami_echo "  ${PURPLE}> ami-setup${NC}     → Run module setup (module_setup.py) with auto-detection${NC}"
    _ami_echo "  ${PURPLE}> ami-install${NC}   → Run comprehensive system installation (install script)${NC}"
    _ami_echo "  ${PURPLE}> ami-git${NC}       → Unified git operations tool${NC}"
    _ami_echo "                    ${GREEN}status${NC}, ${GREEN}diff${NC}, ${GREEN}log${NC}, ${GREEN}commit${NC}, ${GREEN}push${NC}, ${GREEN}pull-all${NC}, ${GREEN}tag-all${NC}"
    _ami_echo ""
    _ami_echo "${GREEN}🤖 AI Agent Interfaces:${NC}"
    _ami_echo "  ${GREEN}> ami-claude${NC}  → Claude Code AI assistant (version-controlled)${NC}"
    _ami_echo "  ${GREEN}> ami-gemini${NC}  → Gemini CLI AI assistant (with auth management)${NC}"
    _ami_echo "  ${GREEN}> ami-qwen${NC}    → Qwen Code AI assistant (version-controlled)${NC}"
    _ami_echo ""
}
