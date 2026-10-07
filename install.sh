#!/usr/bin/env bash
#
# install.sh - Installer for mechubsec/fwskillsshare Claude Code / Codex / Hermes skills
#
# Usage: git clone --branch <tag> --depth 1 https://github.com/mechubsec/fwskillsshare.git
#        cd fwskillsshare && ./install.sh
#
# Piping this script straight from curl into bash is deliberately not offered:
# it would run whatever main currently contains, with no checksum or signature
# check possible before execution. Clone a tagged release (or download that
# tag's tarball) and run install.sh from it instead.
#
# The skill payload under skills/ is verified against skills/CHECKSUMS.sha256
# before anything is copied. A tampered or incomplete payload aborts the
# install. --ref pins a release tag, not a signature; signature verification is
# not implemented yet, and FWSKILLS_REQUIRE_SIGNATURE=1 fails closed until it is.
#
# Options:
#   --all                 Select every skill in the inventory
#   --skill NAME          Select a specific skill by name (repeatable)
#   --family NAME         Select a whole family: parsers | srx | tooling | compliance | deployment (repeatable)
#   --target WHERE        claude | codex | hermes | both | all
#                         ('both' keeps the legacy Claude+Hermes meaning; default: prompt, or claude with -y)
#   --dir PATH            Explicit install directory (overrides --target)
#   --ref TAG             Release tag to install from when downloading (default: GITHUB_REF_DEFAULT below).
#                         Must match vX.Y.Z; branches, HEAD, and other moving refs are refused.
#   --list                Print the skill inventory (grouped by family) and exit
#   --uninstall           Remove the selected skills from the selected target(s) instead of installing
#   --force               Overwrite existing skill directories without prompting
#   -y, --yes             Non-interactive; assume defaults, no prompts
#   -h, --help             Show help and exit
#

set -euo pipefail

# Skill inventory
# BEGIN generated-inventory
declare -a PARSERS=(
    "parsing-cisco-configs"
    "parsing-firepower-configs"
    "parsing-fortinet-configs"
    "parsing-palo-configs"
    "parsing-srx-configs"
)

declare -a SRX=(
    "srx-initial-setup"
    "srx-dynamic-ip-feed"
    "srx-mpls-in-flow"
    "srx-mnha"
    "srx-nat"
    "srx-policy"
    "srx-autovpn-full-tunnel"
    "srx-ipsec-hub-spoke"
    "srx-license-signature-maintenance"
    "srx-advpn"
    "srx-chassis-cluster-proxmox"
    "srx-syslog-logging"
    "srx-ips"
    "srx-mnha-builder"
    "srx-cluster-to-mnha"
)

declare -a TOOLING=(
    "firewall-best-practices-audit"
    "firewall-config-conversion"
    "firewall-config-diff"
)

declare -a COMPLIANCE=(
    "pci-ngfw-compliance"
    "hipaa-ngfw-compliance"
    "cmmc-nist-800-171-ngfw-compliance"
    "cis-controls-ngfw-compliance"
    "iso27001-ngfw-compliance"
    "soc2-ngfw-compliance"
    "srx-disa-stig-compliance"
)

declare -a DEPLOYMENT=(
    "clearpass-proxmox-deploy"
    "sd-onprem-proxmox-deploy"
    "csrx-proxmox-deploy"
)
# END generated-inventory

# Retired skills — renamed into, or merged into, another skill.
# Entries are NEVER removed from this list once added: it is the permanent
# record of every name this repository has stopped shipping. The installer
# deletes these directories from the target on every run, install or uninstall,
# so an existing installation cannot keep serving guidance that was corrected
# or withdrawn. scripts/check-installer.py enforces that this list stays
# disjoint from the live inventory.
declare -a RETIRED_SKILLS=(
    "srx-idp-triage"
    "srx-custom-signature-builder"
    "srx-idp"
)

TOTAL_SKILLS=$((
    ${#PARSERS[@]} +
    ${#SRX[@]} +
    ${#TOOLING[@]} +
    ${#COMPLIANCE[@]} +
    ${#DEPLOYMENT[@]}
))

# Constants
GITHUB_REPO="mechubsec/fwskillsshare"
# Pinned release tag used when downloading skills. Update on every release.
# Never point this at a branch or HEAD -- validate_ref() below refuses anything
# that isn't a vX.Y.Z tag, so a moving ref can't slip in via this default either.
#
# NOTE: When cutting a new release, update this to the release tag (e.g. v1.10.0).
# The checksum manifest (skills/CHECKSUMS.sha256) was added after v1.7.0, so
# this must point to a tag that includes the manifest.
GITHUB_REF_DEFAULT="v1.10.0"
GITHUB_REF="$GITHUB_REF_DEFAULT"
CLAUDE_SKILLS_DIR="${HOME}/.claude/skills"
CODEX_SKILLS_DIR="${HOME}/.agents/skills"
HERMES_SKILLS_DIR="${HOME}/.hermes/skills/devops"

# ANSI colors (only when stdout is a TTY)
if [ -t 1 ]; then
    C_RESET='\033[0m'
    C_BOLD='\033[1m'
    C_GREEN='\033[32m'
    C_BLUE='\033[34m'
    C_YELLOW='\033[33m'
    C_RED='\033[31m'
    C_CYAN='\033[36m'
else
    C_RESET=''
    C_BOLD=''
    C_GREEN=''
    C_BLUE=''
    C_YELLOW=''
    C_RED=''
    C_CYAN=''
fi

# Global variables
TEMP_DIR=""
SELECTED_SKILLS=()
INSTALL_TARGETS=()
EXPLICIT_DIR=""
REF_EXPLICIT=false
MODE="install"
FORCE=false
NON_INTERACTIVE=false

# Cleanup trap
cleanup() {
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
}
trap cleanup EXIT

# Helper functions
print_banner() {
    echo -e "${C_CYAN}${C_BOLD}"
    cat << 'EOF'
╔═══════════════════════════════════════════════╗
║  FW Skills Share - Installer                  ║
║  mechubsec/fwskillsshare                      ║
╚═══════════════════════════════════════════════╝
EOF
    echo -e "${C_RESET}"
}

print_help() {
    cat << EOF
Usage: install.sh [options]

Options:
  --all                 Select all ${TOTAL_SKILLS} skills
  --skill NAME          Select a specific skill by name (repeatable)
  --family NAME         Select a whole family: parsers | srx | tooling | compliance | deployment (repeatable)
  --target WHERE        claude | codex | hermes | both | all
                        ('both' means Claude+Hermes; default: interactive prompt, or claude with -y)
  --dir PATH            Explicit install directory (overrides --target)
  --ref TAG             Release tag to download (default: ${GITHUB_REF_DEFAULT}). Must be vX.Y.Z.
  --list                Print the skill inventory (grouped by family) and exit
  --uninstall           Remove the selected skills from the selected target(s) instead of installing
  --force               Overwrite existing skill directories without prompting
  -y, --yes             Non-interactive; assume defaults, no prompts
  -h, --help             Show help and exit

Examples:
  ./install.sh --all --target claude
  ./install.sh --all --target codex
  ./install.sh --family srx --target both --force
  ./install.sh --family parsers --target all
  ./install.sh --family deployment --target codex
  ./install.sh --skill srx-nat --skill srx-policy
  ./install.sh --all -y --ref ${GITHUB_REF_DEFAULT}

  # From a fresh checkout, no local clone required:
  git clone --branch ${GITHUB_REF_DEFAULT} --depth 1 https://github.com/${GITHUB_REPO}.git
  cd fwskillsshare && ./install.sh --all -y
EOF
}

print_inventory() {
    echo -e "${C_BOLD}Skill Inventory (${TOTAL_SKILLS} total):${C_RESET}\n"

    echo -e "${C_BLUE}Parsers (${#PARSERS[@]}):${C_RESET}"
    for skill in "${PARSERS[@]}"; do
        echo "  - $skill"
    done
    echo ""

    echo -e "${C_BLUE}SRX (${#SRX[@]}):${C_RESET}"
    for skill in "${SRX[@]}"; do
        echo "  - $skill"
    done
    echo ""

    echo -e "${C_BLUE}Tooling (${#TOOLING[@]}):${C_RESET}"
    for skill in "${TOOLING[@]}"; do
        echo "  - $skill"
    done
    echo ""

    echo -e "${C_BLUE}Compliance (${#COMPLIANCE[@]}):${C_RESET}"
    for skill in "${COMPLIANCE[@]}"; do
        echo "  - $skill"
    done
    echo ""

    echo -e "${C_BLUE}Deployment (${#DEPLOYMENT[@]}):${C_RESET}"
    for skill in "${DEPLOYMENT[@]}"; do
        echo "  - $skill"
    done
}

get_all_skills() {
    local -a all_skills=()
    all_skills+=("${PARSERS[@]}")
    all_skills+=("${SRX[@]}")
    all_skills+=("${TOOLING[@]}")
    all_skills+=("${COMPLIANCE[@]}")
    all_skills+=("${DEPLOYMENT[@]}")
    echo "${all_skills[@]}"
}

get_family_skills() {
    local family="$1"
    case "$family" in
        parsers)
            echo "${PARSERS[@]}"
            ;;
        srx)
            echo "${SRX[@]}"
            ;;
        tooling)
            echo "${TOOLING[@]}"
            ;;
        compliance)
            echo "${COMPLIANCE[@]}"
            ;;
        deployment)
            echo "${DEPLOYMENT[@]}"
            ;;
        *)
            echo -e "${C_RED}Error: Unknown family '$family'${C_RESET}" >&2
            echo "Valid families: parsers, srx, tooling, compliance, deployment" >&2
            exit 1
            ;;
    esac
}

skill_exists() {
    local needle="$1"
    local -a all_skills
    read -r -a all_skills <<< "$(get_all_skills)"
    for skill in "${all_skills[@]}"; do
        if [[ "$skill" == "$needle" ]]; then
            return 0
        fi
    done
    return 1
}

# Literal (non-regex) membership test for an array.
# Avoids SC2076 false positives when values contain regex metacharacters.
# Sort and de-duplicate skill names into SELECTED_SKILLS.
#
# Deliberately a read loop rather than `mapfile`: mapfile is a Bash 4 builtin,
# and this script runs under whatever bash the machine ships, cloned or not.
# macOS still ships 3.2, where mapfile aborts the run with
# "mapfile: command not found" before a single skill is copied.
set_selected_skills_sorted() {
    if [[ $# -eq 0 ]]; then
        SELECTED_SKILLS=()
        return 0
    fi
    local -a deduped=()
    local entry
    while IFS= read -r entry; do
        [[ -n "$entry" ]] && deduped+=("$entry")
    done < <(printf '%s\n' "$@" | sort -u)
    if [[ ${#deduped[@]} -eq 0 ]]; then
        SELECTED_SKILLS=()
    else
        SELECTED_SKILLS=("${deduped[@]}")
    fi
}

contains_element() {
    local needle=$1
    shift
    local element
    for element in "$@"; do
        [[ $element == "$needle" ]] && return 0
    done
    return 1
}

validate_ref() {
    local ref="$1"
    if [[ ! "$ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${C_RED}Error: --ref must be a release tag matching vX.Y.Z (got '$ref')${C_RESET}" >&2
        echo -e "${C_RED}Refusing to install from a moving ref such as a branch name or HEAD.${C_RESET}" >&2
        exit 1
    fi
}

sha256_of() {
    local file="$1"
    if command -v sha256sum &>/dev/null; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        echo -e "${C_RED}Error: neither sha256sum nor shasum is available; cannot verify checksums${C_RESET}" >&2
        exit 1
    fi
}

# Verify every file listed in skills_dir/CHECKSUMS.sha256 against its recorded
# hash. Aborts the install (rather than returning an error) on any mismatch,
# missing file, or missing manifest: a corrupted or tampered payload must never
# reach install_skill.
verify_checksums() {
    local skills_dir="$1"
    local manifest="$skills_dir/CHECKSUMS.sha256"

    if [[ ! -f "$manifest" ]]; then
        echo -e "${C_RED}Error: no checksum manifest at $manifest${C_RESET}" >&2
        echo -e "${C_RED}Refusing to install an unverified skill payload.${C_RESET}" >&2
        exit 1
    fi

    # Check for a hasher once at the top, outside any command substitution
    if ! command -v sha256sum &>/dev/null && ! command -v shasum &>/dev/null; then
        echo -e "${C_RED}Error: neither sha256sum nor shasum is available; cannot verify checksums${C_RESET}" >&2
        exit 1
    fi

    echo -e "${C_CYAN}Verifying skill checksums against $manifest...${C_RESET}"

    local line expected relative file_path actual
    local -i checked=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Reject empty lines
        [[ -z "$line" ]] && continue

        # Validate line format: must match ^[0-9a-f]{64}  .+$
        local regex='^[0-9a-f]{64}  .+$'
        if ! [[ "$line" =~ $regex ]]; then
            echo -e "${C_RED}Error: malformed manifest line at $manifest:${C_RESET}" >&2
            echo -e "${C_RED}  $line${C_RESET}" >&2
            echo -e "${C_RED}Expected: <sha256>  <relative-path>${C_RESET}" >&2
            exit 1
        fi

        # Reject absolute paths or paths containing ..
        expected="${line%%  *}"
        relative="${line#*  }"
        if [[ "$relative" == /* ]] || [[ "$relative" == *..* ]]; then
            echo -e "${C_RED}Error: manifest line contains absolute path or ..:${C_RESET}" >&2
            echo -e "${C_RED}  $line${C_RESET}" >&2
            exit 1
        fi
        file_path="$skills_dir/$relative"
        if [[ ! -f "$file_path" ]]; then
            echo -e "${C_RED}Error: checksum manifest lists '$relative' but it is missing from the download${C_RESET}" >&2
            exit 1
        fi
        if command -v sha256sum &>/dev/null; then
            actual=$(sha256sum "$file_path" | awk '{print $1}')
        else
            actual=$(shasum -a 256 "$file_path" | awk '{print $1}')
        fi
        if [[ "$actual" != "$expected" ]]; then
            echo -e "${C_RED}Error: checksum mismatch for '$relative'${C_RESET}" >&2
            echo -e "${C_RED}Refusing to install a skill payload that does not match its manifest.${C_RESET}" >&2
            exit 1
        fi
        ((checked++)) || true
    done < "$manifest"

    # F3+F4: Ensure manifest is not empty and matches exactly
    if (( checked == 0 )); then
        echo -e "${C_RED}Error: checksum manifest $manifest lists no files${C_RESET}" >&2
        exit 1
    fi
    # R1: a symlink anywhere in the payload could point outside it (and was
    # installed as-is), so refuse any at all rather than try to vet targets.
    if [[ -n "$(find "$skills_dir" -type l -print -quit)" ]]; then
        echo -e "${C_RED}Error: symlink(s) present under $skills_dir; refusing to install an unverifiable payload${C_RESET}" >&2
        exit 1
    fi
    local listed present
    listed=$(sed 's/^[0-9a-f]\{64\}  //' "$manifest" | LC_ALL=C sort)
    # Every non-directory entry except the top-level manifest itself: a nested
    # file named CHECKSUMS.sha256 must be listed like any other file.
    present=$(cd "$skills_dir" && find . ! -type d ! -path './CHECKSUMS.sha256' | sed 's|^\./||' | LC_ALL=C sort)
    if [[ "$listed" != "$present" ]]; then
        echo -e "${C_RED}Error: files under $skills_dir do not match the manifest exactly (unlisted or extra files present)${C_RESET}" >&2
        exit 1
    fi

    echo -e "${C_GREEN}✓${C_RESET} $checked file(s) matched the checksum manifest"
}

# Stub: no signing mechanism exists yet (it depends on the release baseline
# work tracked separately). This deliberately fails closed rather than
# pretending to verify something it cannot. Once signing lands, this function
# gets a real implementation instead of a flag that always refuses.
verify_signature() {
    local manifest="$1"

    if [[ "${FWSKILLS_REQUIRE_SIGNATURE:-0}" != "1" ]]; then
        return 0
    fi

    echo -e "${C_RED}Error: FWSKILLS_REQUIRE_SIGNATURE=1 but signature verification is not implemented yet.${C_RESET}" >&2
    echo -e "${C_RED}There is no signature over $manifest that this installer can check.${C_RESET}" >&2
    echo -e "${C_RED}Refusing to install rather than accepting an unsigned manifest as if it were signed.${C_RESET}" >&2
    exit 1
}

detect_script_dir() {
    # Try to detect the directory where the script lives
    # This is tricky when piped from curl
    if [[ -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]]; then
        dirname "$(readlink -f "${BASH_SOURCE[0]}")"
    elif [[ -f "$0" ]]; then
        dirname "$(readlink -f "$0")"
    else
        # Piped from curl, no reliable script dir
        echo ""
    fi
}

find_skills_source() {
    # Returns the path to the skills/ directory
    # Either local (if exists next to script) or downloaded to temp dir

    local script_dir
    script_dir=$(detect_script_dir)

    # Check for local skills/ directory
    if [[ -n "$script_dir" && -d "$script_dir/skills" ]]; then
        if [[ "$REF_EXPLICIT" == true ]]; then
            echo -e "${C_YELLOW}Warning: local skills/ directory found; ignoring explicit --ref ${GITHUB_REF}${C_RESET}" >&2
        fi
        echo "$script_dir/skills"
        return 0
    fi

    # Need to download - create temp dir
    TEMP_DIR=$(mktemp -d)
    echo -e "${C_YELLOW}Downloading skills from GitHub...${C_RESET}" >&2

    # Try curl + tar first (preferred)
    if command -v curl &>/dev/null && command -v tar &>/dev/null; then
        local tarball_url="https://codeload.github.com/${GITHUB_REPO}/tar.gz/refs/tags/${GITHUB_REF}"
        # GitHub's tarball strips a leading 'v' from a vX.Y.Z tag when naming
        # the extracted directory (verified against codeload.github.com).
        if curl -fsSL "$tarball_url" | tar -xz -C "$TEMP_DIR" 2>/dev/null; then
            echo "$TEMP_DIR/fwskillsshare-${GITHUB_REF#v}/skills"
            return 0
        else
            echo -e "${C_RED}Error: Failed to download tarball for tag ${GITHUB_REF}${C_RESET}" >&2
        fi
    fi

    # Fall back to git clone
    if command -v git &>/dev/null; then
        local clone_url="https://github.com/${GITHUB_REPO}.git"
        if git clone --depth 1 --branch "$GITHUB_REF" "$clone_url" "$TEMP_DIR/repo" &>/dev/null; then
            echo "$TEMP_DIR/repo/skills"
            return 0
        else
            echo -e "${C_RED}Error: Failed to clone repository at tag ${GITHUB_REF}${C_RESET}" >&2
        fi
    fi

    echo -e "${C_RED}Error: Neither curl/tar nor git available for download${C_RESET}" >&2
    exit 1
}

interactive_skill_selection() {
    # Print numbered inventory
    echo -e "${C_BOLD}Select skills to install:${C_RESET}\n"

    local idx=1
    local -a all_skills=()

    echo -e "${C_BLUE}Parsers:${C_RESET}"
    for skill in "${PARSERS[@]}"; do
        printf "  %2d) %s\n" $idx "$skill"
        all_skills+=("$skill")
        ((idx++))
    done
    echo ""

    echo -e "${C_BLUE}SRX:${C_RESET}"
    for skill in "${SRX[@]}"; do
        printf "  %2d) %s\n" $idx "$skill"
        all_skills+=("$skill")
        ((idx++))
    done
    echo ""

    echo -e "${C_BLUE}Tooling:${C_RESET}"
    for skill in "${TOOLING[@]}"; do
        printf "  %2d) %s\n" $idx "$skill"
        all_skills+=("$skill")
        ((idx++))
    done
    echo ""

    echo -e "${C_BLUE}Compliance:${C_RESET}"
    for skill in "${COMPLIANCE[@]}"; do
        printf "  %2d) %s\n" $idx "$skill"
        all_skills+=("$skill")
        ((idx++))
    done
    echo ""

    echo -e "${C_BLUE}Deployment:${C_RESET}"
    for skill in "${DEPLOYMENT[@]}"; do
        printf "  %2d) %s\n" $idx "$skill"
        all_skills+=("$skill")
        ((idx++))
    done
    echo ""

    echo "Enter selection (space/comma-separated numbers, ranges like 3-7, or 'a'/'all' for everything):"

    # Read from /dev/tty if available
    local input
    local retries=0
    while [[ $retries -lt 3 ]]; do
        if [[ -r /dev/tty ]]; then
            read -r input < /dev/tty || true
        else
            echo -e "${C_YELLOW}Note: /dev/tty not available, installing all skills${C_RESET}" >&2
            read -r -a SELECTED_SKILLS <<< "$(get_all_skills)"
            return 0
        fi

        # Parse input
        if [[ "$input" =~ ^(a|all)$ ]]; then
            SELECTED_SKILLS=("${all_skills[@]}")
            return 0
        fi

        # Parse numbers and ranges
        local -a selected_indices=()
        # Replace commas with spaces
        input="${input//,/ }"

        local valid=true
        for token in $input; do
            if [[ "$token" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                # Range
                local start="${BASH_REMATCH[1]}"
                local end="${BASH_REMATCH[2]}"
                for ((i=start; i<=end; i++)); do
                    selected_indices+=("$i")
                done
            elif [[ "$token" =~ ^[0-9]+$ ]]; then
                # Single number
                selected_indices+=("$token")
            else
                valid=false
                break
            fi
        done

        if [[ "$valid" == true ]]; then
            # Validate indices and collect skills
            local -a result=()
            for idx in "${selected_indices[@]}"; do
                if ((idx >= 1 && idx <= ${#all_skills[@]})); then
                    result+=("${all_skills[$((idx-1))]}")
                else
                    valid=false
                    break
                fi
            done

            if [[ "$valid" == true && ${#result[@]} -gt 0 ]]; then
                # Remove duplicates
                set_selected_skills_sorted "${result[@]}"
                return 0
            fi
        fi

        echo -e "${C_RED}Invalid selection. Please try again.${C_RESET}"
        ((retries++))
    done

    # Max retries exceeded, install all
    echo -e "${C_YELLOW}Max retries exceeded, installing all skills${C_RESET}"
    SELECTED_SKILLS=("${all_skills[@]}")
}

interactive_target_selection() {
    echo ""
    echo "Select installation target:"
    echo "  1) Claude Code (~/.claude/skills/)"
    echo "  2) Codex (~/.agents/skills/)"
    echo "  3) Hermes (~/.hermes/skills/devops/)"
    echo "  4) Claude Code + Hermes (legacy 'both')"
    echo "  5) All three"
    echo ""
    echo -n "Enter choice [1-5] (default: 1): "

    local input
    if [[ -r /dev/tty ]]; then
        read -r input < /dev/tty || input="1"
    else
        input="1"
    fi

    case "$input" in
        1|"")
            INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR")
            ;;
        2)
            INSTALL_TARGETS=("$CODEX_SKILLS_DIR")
            ;;
        3)
            INSTALL_TARGETS=("$HERMES_SKILLS_DIR")
            ;;
        4)
            INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR" "$HERMES_SKILLS_DIR")
            ;;
        5)
            INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR" "$CODEX_SKILLS_DIR" "$HERMES_SKILLS_DIR")
            ;;
        *)
            echo -e "${C_YELLOW}Invalid choice, defaulting to Claude Code${C_RESET}"
            INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR")
            ;;
    esac
}

install_skill() {
    local skill_name="$1"
    local source_dir="$2"
    local target_dir="$3"

    local skill_source="$source_dir/$skill_name"
    local skill_dest="$target_dir/$skill_name"

    if [[ ! -d "$skill_source" ]]; then
        echo -e "  ${C_RED}✗${C_RESET} $skill_name (not found in source)"
        return 1
    fi

    # Check if destination exists
    if [[ -d "$skill_dest" ]]; then
        if [[ "$FORCE" == true ]]; then
            if ! rm -rf "$skill_dest"; then
                echo -e "  ${C_RED}✗${C_RESET} $skill_name (could not remove existing destination)"
                return 1
            fi
        elif [[ "$NON_INTERACTIVE" == true ]]; then
            echo -e "  ${C_YELLOW}•${C_RESET} $skill_name (skipped, already exists)"
            return 2
        else
            # Ask user
            echo -n "  $skill_name already exists. Overwrite? [y/N]: "
            local answer
            if [[ -r /dev/tty ]]; then
                read -r answer < /dev/tty || answer="n"
            else
                answer="n"
            fi

            if [[ "$answer" =~ ^[Yy]$ ]]; then
                if ! rm -rf "$skill_dest"; then
                    echo -e "  ${C_RED}✗${C_RESET} $skill_name (could not remove existing destination)"
                    return 1
                fi
            else
                echo -e "  ${C_YELLOW}•${C_RESET} $skill_name (skipped)"
                return 2
            fi
        fi
    fi

    # Copy skill
    if ! mkdir -p "$target_dir"; then
        echo -e "  ${C_RED}✗${C_RESET} $skill_name (could not create target directory)"
        return 1
    fi
    if ! cp -r "$skill_source" "$skill_dest"; then
        echo -e "  ${C_RED}✗${C_RESET} $skill_name (copy failed)"
        return 1
    fi
    echo -e "  ${C_GREEN}✓${C_RESET} $skill_name"
    return 0
}

remove_retired_skills() {
    local target_dir="$1"

    # Never operate on an empty path: "$target_dir/$skill" with an unset
    # target_dir would expand to an absolute path at the filesystem root.
    if [[ -z "$target_dir" ]]; then
        echo -e "${C_RED}Error: target directory is empty or unset${C_RESET}" >&2
        return 1
    fi

    if [[ ! -d "$target_dir" ]]; then
        return 0
    fi

    local retired
    for retired in "${RETIRED_SKILLS[@]}"; do
        local retired_path="$target_dir/$retired"
        if [[ -d "$retired_path" ]]; then
            if rm -rf "$retired_path"; then
                echo -e "  ${C_YELLOW}•${C_RESET} removed retired skill: $retired"
            else
                echo -e "  ${C_RED}✗${C_RESET} could not remove retired skill: $retired" >&2
            fi
        fi
    done
}

uninstall_skill() {
    local skill_name="$1"
    local target_dir="$2"

    local skill_dest="$target_dir/$skill_name"

    if [[ -d "$skill_dest" ]]; then
        if ! rm -rf "$skill_dest"; then
            echo -e "  ${C_RED}✗${C_RESET} $skill_name (remove failed)"
            return 1
        fi
        echo -e "  ${C_GREEN}✓${C_RESET} $skill_name (removed)"
        return 0
    else
        echo -e "  ${C_YELLOW}•${C_RESET} $skill_name (not found)"
        return 2
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            read -r -a SELECTED_SKILLS <<< "$(get_all_skills)"
            shift
            ;;
        --skill)
            if [[ -z "${2:-}" ]]; then
                echo -e "${C_RED}Error: --skill requires a skill name${C_RESET}" >&2
                exit 1
            fi
            if ! skill_exists "$2"; then
                echo -e "${C_RED}Error: Unknown skill '$2'${C_RESET}" >&2
                exit 1
            fi
            SELECTED_SKILLS+=("$2")
            shift 2
            ;;
        --family)
            if [[ -z "${2:-}" ]]; then
                echo -e "${C_RED}Error: --family requires a family name${C_RESET}" >&2
                exit 1
            fi
            # get_family_skills exits non-zero on an unknown family. Capture it
            # in its own assignment so that status is still visible: inside a
            # here-string the substitution's status is discarded and an invalid
            # family would be silently accepted.
            family_skills=$(get_family_skills "$2") || exit 1
            declare -a _tmp_family_skills
            read -r -a _tmp_family_skills <<< "$family_skills"
            SELECTED_SKILLS+=("${_tmp_family_skills[@]}")
            shift 2
            ;;
        --target)
            if [[ -z "${2:-}" ]]; then
                echo -e "${C_RED}Error: --target requires claude, codex, hermes, both, or all${C_RESET}" >&2
                exit 1
            fi
            case "$2" in
                claude)
                    INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR")
                    ;;
                codex)
                    INSTALL_TARGETS=("$CODEX_SKILLS_DIR")
                    ;;
                hermes)
                    INSTALL_TARGETS=("$HERMES_SKILLS_DIR")
                    ;;
                both)
                    INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR" "$HERMES_SKILLS_DIR")
                    ;;
                all)
                    INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR" "$CODEX_SKILLS_DIR" "$HERMES_SKILLS_DIR")
                    ;;
                *)
                    echo -e "${C_RED}Error: --target must be claude, codex, hermes, both, or all${C_RESET}" >&2
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        --dir)
            if [[ -z "${2:-}" ]]; then
                echo -e "${C_RED}Error: --dir requires a path${C_RESET}" >&2
                exit 1
            fi
            EXPLICIT_DIR="$2"
            shift 2
            ;;
        --ref)
            if [[ -z "${2:-}" ]]; then
                echo -e "${C_RED}Error: --ref requires a release tag${C_RESET}" >&2
                exit 1
            fi
            validate_ref "$2"
            GITHUB_REF="$2"
            REF_EXPLICIT=true
            shift 2
            ;;
        --list)
            print_inventory
            exit 0
            ;;
        --uninstall)
            MODE="uninstall"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -y|--yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -h|--help)
            print_help
            exit 0
            ;;
        *)
            echo -e "${C_RED}Error: Unknown option '$1'${C_RESET}" >&2
            echo "Run with --help for usage information" >&2
            exit 1
            ;;
    esac
done

# Main execution
print_banner

# Determine skill selection
if [[ ${#SELECTED_SKILLS[@]} -eq 0 ]]; then
    if [[ "$NON_INTERACTIVE" == true ]]; then
        # With -y and no selection, install all
        read -r -a SELECTED_SKILLS <<< "$(get_all_skills)"
    else
        # Interactive selection
        interactive_skill_selection
    fi
fi

# Remove duplicates from selected skills
set_selected_skills_sorted "${SELECTED_SKILLS[@]}"

# Determine install targets
if [[ -n "$EXPLICIT_DIR" ]]; then
    INSTALL_TARGETS=("$EXPLICIT_DIR")
elif [[ ${#INSTALL_TARGETS[@]} -eq 0 ]]; then
    if [[ "$NON_INTERACTIVE" == true ]]; then
        INSTALL_TARGETS=("$CLAUDE_SKILLS_DIR")
    else
        interactive_target_selection
    fi
fi

# Summary
echo ""
if [[ "$MODE" == "install" ]]; then
    echo -e "${C_BOLD}Installing ${#SELECTED_SKILLS[@]} skill(s) to ${#INSTALL_TARGETS[@]} target(s)${C_RESET}"
else
    echo -e "${C_BOLD}Uninstalling ${#SELECTED_SKILLS[@]} skill(s) from ${#INSTALL_TARGETS[@]} target(s)${C_RESET}"
fi
echo ""

# Find skills source (only needed for install)
SKILLS_SOURCE=""
if [[ "$MODE" == "install" ]]; then
    SKILLS_SOURCE=$(find_skills_source)
    echo ""
    verify_checksums "$SKILLS_SOURCE"
    verify_signature "$SKILLS_SOURCE/CHECKSUMS.sha256"
    echo ""
fi

# Process each target
declare -i installed=0
declare -i skipped=0
declare -i failed=0

for target in "${INSTALL_TARGETS[@]}"; do
    echo -e "${C_CYAN}Target: $target${C_RESET}"

    # Runs for install and uninstall alike, regardless of what was selected.
    remove_retired_skills "$target"

    for skill in "${SELECTED_SKILLS[@]}"; do
        if [[ "$MODE" == "install" ]]; then
            if install_skill "$skill" "$SKILLS_SOURCE" "$target"; then
                ((installed++)) || true
            else
                rc=$?
                if [[ $rc -eq 2 ]]; then
                    ((skipped++)) || true
                else
                    ((failed++)) || true
                fi
            fi
        else
            if uninstall_skill "$skill" "$target"; then
                ((installed++)) || true
            else
                rc=$?
                if [[ $rc -eq 2 ]]; then
                    ((skipped++)) || true
                else
                    ((failed++)) || true
                fi
            fi
        fi
    done

    echo ""
done

# Final summary
echo -e "${C_BOLD}Summary:${C_RESET}"
if [[ "$MODE" == "install" ]]; then
    echo -e "  ${C_GREEN}✓${C_RESET} $installed installed"
    echo -e "  ${C_YELLOW}•${C_RESET} $skipped skipped"
    echo -e "  ${C_RED}✗${C_RESET} $failed failed"
else
    echo -e "  ${C_GREEN}✓${C_RESET} $installed removed"
    echo -e "  ${C_YELLOW}•${C_RESET} $skipped not found"
    echo -e "  ${C_RED}✗${C_RESET} $failed failed"
fi
echo ""
echo -e "${C_BOLD}Target paths:${C_RESET}"
for target in "${INSTALL_TARGETS[@]}"; do
    echo "  $target"
done

if [[ "$MODE" == "install" && $installed -gt 0 ]]; then
    echo ""
    echo -e "${C_BOLD}Next steps:${C_RESET}"
    if contains_element "$CLAUDE_SKILLS_DIR" "${INSTALL_TARGETS[@]}"; then
        echo "  • Restart Claude Code — skills auto-trigger on vendor keywords / pasted configs"
    fi
    if contains_element "$CODEX_SKILLS_DIR" "${INSTALL_TARGETS[@]}"; then
        echo "  • Codex detects skill changes automatically; restart Codex if they do not appear"
    fi
    if contains_element "$HERMES_SKILLS_DIR" "${INSTALL_TARGETS[@]}"; then
        echo "  • Run 'hermes skills list' to verify installation"
    fi
fi

echo ""
if ((failed > 0)); then
    echo -e "${C_RED}${C_BOLD}Completed with errors.${C_RESET}"
    exit 1
fi

echo -e "${C_GREEN}${C_BOLD}Done!${C_RESET}"
