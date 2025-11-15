"""Version information for the backend."""

VERSION = "1.0.5"
BUILD_DATE = "2025-11-15"

def get_version_info():
    """Get version information as a dictionary."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "component": "backend"
    }
