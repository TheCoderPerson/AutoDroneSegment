"""Version information for the backend."""

VERSION = "1.0.3"
BUILD_DATE = "2025-11-14"

def get_version_info():
    """Get version information as a dictionary."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "component": "backend"
    }
