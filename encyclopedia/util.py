from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def list_entries():
    """Return the names of all saved encyclopedia entries."""
    _, filenames = default_storage.listdir("entries")
    return sorted(name[:-3] for name in filenames if name.endswith(".md"))


def save_entry(title, content):
    """Save an entry's Markdown content, replacing any existing content."""
    filename = f"entries/{title}.md"
    if default_storage.exists(filename):
        default_storage.delete(filename)
    default_storage.save(filename, ContentFile(content))


def get_entry(title):
    """Return an entry's Markdown content, or None if it does not exist."""
    try:
        with default_storage.open(f"entries/{title}.md") as entry:
            return entry.read().decode("utf-8")
    except FileNotFoundError:
        return None
