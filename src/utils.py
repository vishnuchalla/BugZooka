import re


def extract_link(text):
    """Check if the message contains 'failure' and extract the first hyperlink (URL)."""
    URL_PATTERN = re.compile(r"(https://[^\s|]+)")
    if "failure" in text.lower():
        match = URL_PATTERN.search(text)
        print(match)
        if match:
            return match.group(0)  # Return extracted URL
    return None