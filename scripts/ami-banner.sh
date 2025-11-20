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
    _ami_echo " \ \    / _ \  _ __   ___  _ __     / \   |  \/  ||_ _|       __   ___   __"
    _ami_echo "  \ \  | | | || '_ \ / _ \| '_ \   / _ \  | |\/| | | |  __ __/  \ |_  ) /  \""
    _ami_echo "  / /  | |_| || |_) |  __/| | | | / ___ \ | |  | | | |  \ V / () | / / | () |"
    _ami_echo " /_/    \___/ | .__/ \___||_| |_|/_/   \_\|_|  |_||___|  \_/ \__(_)___(_)__/"
    _ami_echo "              |_|"
    _ami_echo ""
    _ami_echo "${GREEN}> Secure infrastructure for distributed enterprise automation and governance."
    _ami_echo "> Supports bare metal, cloud, and hybrid deployments without vendor lock-in."
    _ami_echo "> Safely integrates with any local or remote web, data, and API service."
    _ami_echo "${RED}"
    _ami_echo "============================================================================="
    _ami_echo "> Transparent and auditable open-source framework by Indepentent AI Labs."
    _ami_echo "> Full NIST AI CSF/RMF, ISO 42001/27001, and EU AI Act compliance."
    _ami_echo "============================================================================="
    _ami_echo "${NC}"
    _ami_echo "${RED}🔴 Core Execution & Management:${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-run${NC}       → Sandboxed universal execution wrapper${NC}"
    _ami_echo "                    ${GREEN}uv/python, node/npm/npx, java, php, podman, ${ORANGE}admin (cli)${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-agent${NC}     → AI agent orchestration and automation${NC}"
    _ami_echo "                    ${GREEN}interactive, planner, automation, learning, ${ORANGE}admin (cli)${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-repo${NC}      → Git repository, server and project management${NC}"
    _ami_echo "                    ${GREEN}git, manage (server), gitlab-api, github-api, hf-api${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-node${NC}      → Infrastructure orchestration and observability${NC}"
    _ami_echo "                    ${GREEN}monitor, scripts, profiles, compliance, ${ORANGE}admin (cli)${NC}"
    _ami_echo ""
    _ami_echo "${PURPLE}🟣 Internal Development Tools:${NC}"
    _ami_echo ""
    _ami_echo "  ${PURPLE}> ami-test${NC}      → Execute pytest, preflight and junit test suites${NC}"
    _ami_echo "  ${PURPLE}> ami-setup${NC}     → Set-up & dependency synchronisation for submodules${NC}"
    _ami_echo "  ${PURPLE}> ami-install${NC}   → Perform deployment maintainance and install updates${NC}"
    _ami_echo ""
    _ami_echo "${RED}🤖 NON-MODERATED Coding Agents (UNSAFE - REQUIRE CONSTANT HUMAN SUPERVISION):${NC}"
    _ami_echo ""
    _ami_echo "  ${RED}> ami-claude${NC}    → Claude Code AI assistant (version-controlled)${NC}"
    _ami_echo "  ${RED}> ami-gemini${NC}    → Gemini CLI AI assistant (with auth management)${NC}"
    _ami_echo "  ${RED}> ami-qwen${NC}      → Qwen Code AI assistant (version-controlled)${NC}"
    _ami_echo ""
}
