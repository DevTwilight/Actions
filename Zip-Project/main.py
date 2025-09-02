import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path

RESET = '\033[0m'
BOLD = '\033[1m'

BRIGHT_RED = '\033[91m'
BRIGHT_GREEN = '\033[38;5;10m'
VIVID_YELLOW = '\033[38;5;226m'
LIGHT_CORNFLOWER_BLUE = "\033[38;2;175;203;255m"

def print_error(msg):
    print(f"{BRIGHT_RED}{BOLD}ERROR: {msg}{RESET}", file=sys.stderr)
    sys.exit(1)

def print_warning(msg):
    print(f"{VIVID_YELLOW}Warning: {msg}{RESET}", file=sys.stderr)

def print_success(msg):
    print(f"{BRIGHT_GREEN}{BOLD}{msg}{RESET}")

def print_info(msg):
    print(f"{LIGHT_CORNFLOWER_BLUE}{msg}{RESET}")

def get_env_var(name, required=False, default=None):
    val = os.getenv(name)
    if val is None or val.strip() == "":
        if required:
            print_error(f"Missing required input environment variable: {name}")
        return default
    return val.strip()

def parse_list_env(var):
    val = get_env_var(var, default="")
    return [line.strip() for line in val.splitlines() if line.strip()]

def copy_includes(includes, dest_dir):
    for path_str in includes:
        src = Path(path_str).resolve()
        if not src.exists():
            print_warning(f"Included path does not exist and will be skipped: {src}")
            continue
        dest = Path(dest_dir) / src.name
        try:
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        except Exception as e:
            print_warning(f"Failed to copy {src} to {dest}: {e}")

def remove_excludes(excludes, temp_dir):
    for rel_path_str in excludes:
        path_to_remove = Path(temp_dir) / rel_path_str
        if path_to_remove.exists():
            try:
                if path_to_remove.is_dir():
                    shutil.rmtree(path_to_remove)
                else:
                    path_to_remove.unlink()
            except Exception as e:
                print_warning(f"Failed to exclude {path_to_remove}: {e}")
        else:
            print_warning(f"Exclude path not found in temp dir and skipped: {path_to_remove}")

def create_zip(zip_path, source_dir, compress_level):
    compression = zipfile.ZIP_DEFLATED if compress_level > 0 else zipfile.ZIP_STORED
    try:
        with zipfile.ZipFile(zip_path, 'w', compression=compression, compresslevel=compress_level if compress_level > 0 else None) as zipf:
            for root, dirs, files in os.walk(source_dir):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
    except TypeError:
        if compress_level > 0:
            print_warning("Compress level ignored (Python version < 3.7).")
        with zipfile.ZipFile(zip_path, 'w', compression=compression) as zipf:
            for root, dirs, files in os.walk(source_dir):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)

def main():
    includes = parse_list_env("INCLUDE")
    if not includes:
        print_error("No paths specified to include.")

    excludes = parse_list_env("EXCLUDE")
    name = get_env_var("NAME", required=True)
    version = get_env_var("VERSION", required=True)
    platform = get_env_var("PLATFORM", required=True)
    arch = get_env_var("ARCH", required=True)
    output_dir = get_env_var("OUTPUT", default=os.getcwd())
    compress_str = get_env_var("COMPRESS", default="6")

    try:
        compress_level = int(compress_str)
        if compress_level < 0 or compress_level > 9:
            raise ValueError()
    except ValueError:
        print_warning(f"Invalid compression level '{compress_str}', defaulting to 6.")
        compress_level = 6

    output_path = Path(output_dir).resolve()
    if not output_path.exists():
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print_error(f"Failed to create output directory '{output_path}': {e}")

    zip_name = f"{name}-{version}-{platform}-{arch}.zip"
    zip_path = output_path / zip_name

    print_info(f"Creating ZIP archive: {zip_path}")
    print_info(f"Including paths: {includes}")
    if excludes:
        print_info(f"Excluding paths: {excludes}")
    else:
        print_info("No paths to exclude.")

    with tempfile.TemporaryDirectory() as temp_dir:
        copy_includes(includes, temp_dir)
        if excludes:
            remove_excludes(excludes, temp_dir)
        create_zip(zip_path, temp_dir, compress_level)

    print_success(f"ZIP archive created successfully: {zip_path}")

main()
