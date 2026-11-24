from datetime import datetime
from pathlib import Path
import re


def sanitize_prefix(raw_prefix: str) -> str:
    """Clean a prefix using regex so it is safe and neat for filenames."""
    cleaned = raw_prefix.strip().replace(" ", "_")
    # Remove characters that are invalid or messy in file names
    cleaned = re.sub(r'[<>:"/\\|?*]+', "", cleaned)
    # Collapse repeated underscores into a single underscore
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "file"


def parse_extensions(ext_input: str) -> set[str] | None:
    """
    Parse user-entered extensions (e.g. '.jpg, .png' or 'jpg png').
    Returns None if the user wants all file types.
    """
    trimmed = ext_input.strip().lower()
    if not trimmed or trimmed in {"all", "*"}:
        return None

    parts = re.split(r"[\s,]+", trimmed)
    extensions: set[str] = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if not part.startswith("."):
            part = f".{part}"
        extensions.add(part)
    return extensions or None


def get_file_date_str(file_path: Path, date_mode: str) -> str:
    """
    Return 'YYYY-MM-DD' using modification ('m') or creation ('c') timestamp.
    """
    stat = file_path.stat()
    if date_mode == "c":
        # On Windows st_ctime is creation time; on many Unix systems st_birthtime is
        timestamp = getattr(stat, "st_birthtime", stat.st_ctime)
    else:
        timestamp = stat.st_mtime

    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")


def get_non_conflicting_path(directory: Path, desired_name: str, reserved_names: set[str]) -> Path:
    """
    Ensure the target filename neither exists on disk nor collides with another
    planned rename in the same batch.
    """
    candidate = directory / desired_name
    if desired_name not in reserved_names and not candidate.exists():
        reserved_names.add(desired_name)
        return candidate

    base = Path(desired_name)
    stem = base.stem
    suffix = base.suffix
    counter = 1

    while True:
        new_name = f"{stem}_dup{counter}{suffix}"
        candidate = directory / new_name
        if new_name not in reserved_names and not candidate.exists():
            reserved_names.add(new_name)
            return candidate
        counter += 1


def sort_key_natural(file_path: Path) -> tuple:
    """Sort naturally so IMG_2.jpg comes before IMG_10.jpg."""
    tokens = re.split(r"(\d+)", file_path.name.lower())
    return tuple(int(token) if token.isdigit() else token for token in tokens)


def build_rename_plan(
    target_dir: Path,
    prefix: str,
    start_num: int,
    allowed_exts: set[str] | None,
    date_mode: str | None,
    pad_width: int = 3,
) -> list[tuple[Path, Path]]:
    """Collect matching files, sort them, and compute (source_path, target_path) pairs."""
    files = [
        item
        for item in target_dir.iterdir()
        if item.is_file() and (allowed_exts is None or item.suffix.lower() in allowed_exts)
    ]
    files.sort(key=sort_key_natural)

    # Reserve names already present in target_dir so we don't clobber untouched files
    existing_names = {item.name for item in target_dir.iterdir()}
    reserved_names = set(existing_names)

    plan: list[tuple[Path, Path]] = []
    current_num = start_num

    for src_path in files:
        # Allow this file's own current name to be reused only if no other file claims it
        reserved_names.discard(src_path.name)

        ext = src_path.suffix.lower()
        number_str = f"{current_num:0{pad_width}d}"

        if date_mode in {"m", "c"}:
            date_prefix = get_file_date_str(src_path, date_mode)
            proposed_name = f"{date_prefix}_{prefix}_{number_str}{ext}"
        else:
            proposed_name = f"{prefix}_{number_str}{ext}"

        dest_path = get_non_conflicting_path(target_dir, proposed_name, reserved_names)
        plan.append((src_path, dest_path))
        current_num += 1

    return plan


def apply_rename_plan(plan: list[tuple[Path, Path]]) -> tuple[int, list[tuple[str, str]]]:
    """
    Execute renames safely using a two-step temporary name when a destination
    already exists on disk (such as swapping or shifting numbered names).
    """
    renamed_count = 0
    errors: list[tuple[str, str]] = []
    temp_steps: list[tuple[Path, Path]] = []

    # Step 1: Move files that would collide with an existing file to a temp name
    for src_path, dest_path in plan:
        if src_path == dest_path:
            continue
        try:
            if dest_path.exists():
                temp_path = dest_path.with_name(f".__tmp_rename_{dest_path.name}")
                src_path.rename(temp_path)
                temp_steps.append((temp_path, dest_path))
            else:
                src_path.rename(dest_path)
                renamed_count += 1
        except OSError as exc:
            errors.append((src_path.name, str(exc)))

    # Step 2: Finalize temporary files into their target names
    for temp_path, dest_path in temp_steps:
        try:
            if dest_path.exists():
                unique_dest = get_non_conflicting_path(dest_path.parent, dest_path.name, set())
                temp_path.rename(unique_dest)
            else:
                temp_path.rename(dest_path)
            renamed_count += 1
        except OSError as exc:
            errors.append((temp_path.name, str(exc)))

    return renamed_count, errors


def main() -> None:
    raw_folder = input("Enter folder path: ").strip().strip('"').strip("'")
    target_dir = Path(raw_folder).expanduser()

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: '{target_dir}' is not a valid folder.")
        return

    raw_prefix = input("Enter filename prefix (e.g. event_photo): ")
    prefix = sanitize_prefix(raw_prefix)

    start_str = input("Enter starting number (default 1): ").strip()
    try:
        start_num = int(start_str) if start_str else 1
        if start_num < 0:
            print("Error: Starting number cannot be negative.")
            return
    except ValueError:
        print("Error: Starting number must be a whole number.")
        return

    ext_input = input("File extensions to rename (e.g. .jpg, .png or 'all' for everything): ")
    allowed_exts = parse_extensions(ext_input)

    date_choice = input("Include date in filename? (n = no, m = modified date, c = created date): ").strip().lower()
    date_mode = date_choice if date_choice in {"m", "c"} else None

    plan = build_rename_plan(
        target_dir=target_dir,
        prefix=prefix,
        start_num=start_num,
        allowed_exts=allowed_exts,
        date_mode=date_mode,
        pad_width=3,
    )

    if not plan:
        print("No matching files found to rename.")
        return

    preview_choice = input("Preview changes before renaming? (y/n): ").strip().lower()
    if preview_choice == "y":
        print("\n--- Preview ---")
        for src_path, dest_path in plan:
            print(f"{src_path.name}  ->  {dest_path.name}")

        confirm = input("\nApply these changes? (y/n): ").strip().lower()
        if confirm != "y":
            print("Operation cancelled. No files were renamed.")
            return

    renamed_count, errors = apply_rename_plan(plan)
    print(f"\nDone. {renamed_count} file(s) renamed.")

    if errors:
        print("\n--- Errors ---")
        for name, reason in errors:
            print(f"- {name}: {reason}")


if __name__ == "__main__":
    main()