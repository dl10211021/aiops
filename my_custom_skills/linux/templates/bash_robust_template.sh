#!/bin/bash
#
# Description: A robust bash script template.
# Author: Gemini CLI
# Date: $(date +%Y-%m-%d)
#

# Strict mode: fail on error, unset vars, and pipe failures
set -euo pipefail
IFS=$'
	'

# Constants
readonly SCRIPT_NAME=$(basename "$0")
readonly LOG_FILE="/var/log/${SCRIPT_NAME%.*}.log"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    local msg="$1"
    echo -e "${GREEN}[INFO]${NC} $(date +'%Y-%m-%d %H:%M:%S') - $msg"
}

log_warn() {
    local msg="$1"
    echo -e "${YELLOW}[WARN]${NC} $(date +'%Y-%m-%d %H:%M:%S') - $msg" >&2
}

log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $(date +'%Y-%m-%d %H:%M:%S') - $msg" >&2
}

# Cleanup function (runs on exit)
cleanup() {
    # Remove temporary files here
    # rm -f "$TEMP_FILE"
    log_info "Script finished."
}
trap cleanup EXIT

# Check for root privileges
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root."
        exit 1
    fi
}

# Main logic
main() {
    log_info "Starting script..."
    
    # Example: Check for dependency
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed."
        exit 1
    fi

    # Your code here
    log_info "Doing some work..."
    sleep 1
    
    log_info "Work complete."
}

# Execute main
main "$@"
