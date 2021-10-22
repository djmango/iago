import unicodedata

def clean_str(s=str()):
    """ custom string cleaner, returns normalized unicode with spaces trimmed

        Args:
            string(str)

        Returns:
            string(str): normalized unicode string with spaces trimmed
    """

    # u = unicodedata.normalize('NFC', str(string.replace('\n', '').strip()))
    u = unicodedata.normalize('NFC', str(s.strip()))
    return u
