# Bulk File Renamer

A Python utility that batch-renames files in a target directory using a custom prefix, sequential numbering, optional date stamps, and safe collision handling. Ideal for organizing camera dumps like `IMG_001.jpg` into clean, consistent filenames such as `event_photo_001.jpg` or `2026-11-21_photo_001.jpg`.

## Features

- **Custom Prefix & Starting Number:** Format files with a sanitized prefix and zero-padded sequence numbers starting from any non-negative integer.
- **File Extension Filtering:** Target specific extensions (e.g., `.jpg, .png`) or rename all files (`all`) while preserving original extensions.
- **Natural Sorting & Date Stamps:** Sort numbered filenames naturally (`IMG_2.jpg` before `IMG_10.jpg`) and optionally prepend file modification (`m`) or creation (`c`) dates (`YYYY-MM-DD`).
- **Dry-Run Preview & Confirmation:** Inspect all `old_name -> new_name` changes before applying them.
- **Overwrite Protection:** Avoids overwriting existing files or colliding planned names using unique suffixes and two-step temporary renames.

## Tech Stack

- **Python 3** (standard library only: `pathlib`, `re`, `datetime`)

## Getting Started

### Prerequisites

- Python 3.9 or higher installed on your system. No external packages required.

### Installation & Usage

1. Clone or download the repository and open a terminal in the project folder:

   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>

2. Run the script:

    python bulk_renamer.py