import os
from pathlib import Path

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Supabase configuration
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

BUCKET_NAME = "hau-corpus"


if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL environment variable is not set.")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "SUPABASE_SERVICE_KEY environment variable is not set."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)


# ============================================================
# Helpers
# ============================================================

def _normalize_storage_path(path: str) -> str:
    """
    Convert a local-style path into a Supabase Storage path.
    """
    return str(path).replace("\\", "/").lstrip("/")


def _content_type(file_path: str | Path) -> str:
    """
    Return the MIME type used for common corpus files.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return "application/pdf"

    if suffix == ".txt":
        return "text/plain"

    return "application/octet-stream"


# ============================================================
# Upload
# ============================================================

def upload_file(
    local_file: str | Path,
    storage_path: str,
    overwrite: bool = True
):
    """
    Upload a local file to Supabase Storage.

    Parameters
    ----------
    local_file:
        Local file to upload.

    storage_path:
        Path inside the hau-corpus bucket, for example:
        promoted/example.pdf

    overwrite:
        Whether an existing object may be replaced.
    """

    local_file = Path(local_file)

    if not local_file.exists():
        raise FileNotFoundError(
            f"Local file not found: {local_file}"
        )

    if not local_file.is_file():
        raise ValueError(
            f"Expected a file, got: {local_file}"
        )

    normalized_path = _normalize_storage_path(storage_path)

    with local_file.open("rb") as file:
        file_data = file.read()

    return supabase.storage.from_(BUCKET_NAME).upload(
        normalized_path,
        file_data,
        {
            "content-type": _content_type(local_file),
            "upsert": "true" if overwrite else "false",
        }
    )


# ============================================================
# Upload raw bytes/text
# ============================================================

def upload_bytes(
    data: bytes,
    storage_path: str,
    content_type: str = "text/plain",
    overwrite: bool = True
):
    """
    Upload bytes directly to Supabase Storage.
    Useful when a file does not need to exist permanently
    on the local filesystem first.
    """

    normalized_path = _normalize_storage_path(storage_path)

    return supabase.storage.from_(BUCKET_NAME).upload(
        normalized_path,
        data,
        {
            "content-type": content_type,
            "upsert": "true" if overwrite else "false",
        }
    )


def upload_text(
    text: str,
    storage_path: str,
    overwrite: bool = True
):
    """
    Upload text directly to Supabase Storage.
    """

    return upload_bytes(
        text.encode("utf-8"),
        storage_path,
        content_type="text/plain",
        overwrite=overwrite
    )


# ============================================================
# Download
# ============================================================

def download_bytes(storage_path: str) -> bytes:
    """
    Download an object from Supabase Storage.
    """

    normalized_path = _normalize_storage_path(storage_path)

    return supabase.storage.from_(BUCKET_NAME).download(
        normalized_path
    )


def download_text(storage_path: str) -> str:
    """
    Download a UTF-8 text file from Supabase Storage.
    """

    return download_bytes(storage_path).decode(
        "utf-8",
        errors="ignore"
    )


def download_to_file(
    storage_path: str,
    local_file: str | Path
):
    """
    Download a Supabase Storage object to a local file.
    """

    local_file = Path(local_file)
    local_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    local_file.write_bytes(
        download_bytes(storage_path)
    )

    return local_file


# ============================================================
# Listing
# ============================================================

def list_files(folder: str):
    """
    List all files directly inside a Supabase Storage folder.

    Supabase Storage returns a limited number of objects per request,
    so this function paginates until all entries have been retrieved.
    """

    normalized_folder = _normalize_storage_path(folder)

    all_entries = []
    offset = 0
    limit = 100

    while True:
        entries = supabase.storage.from_(BUCKET_NAME).list(
            normalized_folder,
            {
                "limit": limit,
                "offset": offset,
                "sortBy": {
                    "column": "name",
                    "order": "asc",
                },
            }
        )

        if not entries:
            break

        all_entries.extend(entries)

        if len(entries) < limit:
            break

        offset += limit

    return all_entries


# ============================================================
# Delete
# ============================================================

def delete_file(storage_path: str):
    """
    Delete one file from Supabase Storage.

    Uses the service-role client and verifies that the object
    is actually gone after the delete operation.
    """

    normalized_path = _normalize_storage_path(storage_path)

    if not normalized_path:
        raise ValueError("Storage path cannot be empty.")

    # Delete the object.
    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .remove([normalized_path])
    )

    # Verify deletion.
    if file_exists(normalized_path):
        raise RuntimeError(
            f"Supabase Storage object was not deleted: "
            f"{normalized_path}"
        )

    return response


# ============================================================
# Exists / fetch helper
# ============================================================

def file_exists(storage_path: str) -> bool:
    """
    Check whether a specific object exists.

    This uses the parent folder listing rather than assuming
    that a direct HEAD request is available through the client.
    """

    normalized_path = _normalize_storage_path(storage_path)

    path = Path(normalized_path)

    folder = str(path.parent).replace("\\", "/")
    filename = path.name

    entries = list_files(folder if folder != "." else "")

    return any(
        entry.get("name") == filename
        for entry in entries
    )


def sync_folder_to_local(
    storage_folder: str,
    local_folder: str | Path,
    extensions: set[str] | None = None
):
    """
    Synchronize files from a Supabase Storage folder into a
    local runtime cache.

    Existing local files that no longer exist in Supabase
    are removed from the cache.

    Files that already exist locally are kept.
    Missing remote files are downloaded.
    """

    local_folder = Path(local_folder)
    local_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    entries = list_files(storage_folder)

    remote_names = set()

    for entry in entries:
        name = entry.get("name")

        if not name:
            continue

        # Ignore subfolders if any appear in the listing.
        if entry.get("id") is None:
            continue

        suffix = Path(name).suffix.lower()

        if extensions and suffix not in extensions:
            continue

        remote_names.add(name)

        local_file = local_folder / name

        # Download only files that are not already cached.
        if not local_file.exists():

            storage_path = (
                f"{storage_folder.rstrip('/')}/{name}"
            )

            print(
                f"[STORAGE] Downloading {storage_path}"
            )

            download_to_file(
                storage_path,
                local_file
            )

    # Remove stale local cache files.
    for local_file in local_folder.iterdir():

        if not local_file.is_file():
            continue

        if extensions:
            if local_file.suffix.lower() not in extensions:
                continue

        if local_file.name not in remote_names:
            print(
                f"[STORAGE] Removing stale cache: "
                f"{local_file.name}"
            )

            local_file.unlink()