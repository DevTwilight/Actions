import sys

RESET = '\033[0m'
BOLD = '\033[1m'

BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[92m'
BRIGHT_YELLOW = '\033[33m'
BRIGHT_CYAN = '\033[96m'


def print_error(msg: str):
    print(f"{BRIGHT_RED}{BOLD}ERROR: {msg}{RESET}", file=sys.stderr)
    sys.exit(1)


def print_warning(msg: str):
    print(f"{BRIGHT_YELLOW}Warning: {msg}{RESET}", file=sys.stderr)


def print_success(msg: str):
    print(f"{BRIGHT_GREEN}{BOLD}{msg}{RESET}")


def print_info(msg: str):
    print(f"{BRIGHT_CYAN}{msg}{RESET}")