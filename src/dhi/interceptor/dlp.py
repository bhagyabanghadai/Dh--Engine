"""High-entropy token detection for DLP (Data Loss Prevention) scanning.

Uses Shannon entropy to identify non-patterned secrets (e.g. base64-encoded
credentials, random API keys) that evade regex-based detectors.
"""

from __future__ import annotations

import math
import re

# Tokens with entropy >= this threshold are flagged as potentially sensitive.
HIGH_ENTROPY_THRESHOLD: float = 4.5

# Tokens shorter than this are ignored (too short to be meaningful secrets).
MIN_TOKEN_LEN: int = 16

# Redaction marker used for high-entropy (non-pattern-confirmed) tokens.
HIGH_ENTROPY_MARKER: str = "<REDACTED_HIGH_ENTROPY>"

# Tokenizer: split on whitespace, quotes, common punctuation, and delimiters.
_TOKENIZER_PATTERN = re.compile(r'[\s\'"=:,;()\[\]{}<>|\\@&#%!?\n\r\t]+')

# Only evaluate tokens that look like they could be a secret:
# Must contain at least one digit or symbol character (not pure alpha words).
_NON_TRIVIAL_PATTERN = re.compile(r"[0-9+/=_\-]")


def shannon_entropy(token: str) -> float:
    """Calculate the Shannon entropy of a string in bits per character.

    A perfectly random ASCII string of 64 characters has entropy ~6.0.
    English prose averages 3.5-4.0. Values above 4.5 suggest encoded secrets.
    """
    if not token:
        return 0.0

    length = len(token)
    frequency: dict[str, int] = {}
    for char in token:
        frequency[char] = frequency.get(char, 0) + 1

    entropy = 0.0
    for count in frequency.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def scan_high_entropy_tokens(content: str) -> list[tuple[str, float]]:
    """Return a list of ``(token, entropy)`` for all over-threshold tokens.

    Only tokens meeting :data:`MIN_TOKEN_LEN` and :data:`HIGH_ENTROPY_THRESHOLD`
    criteria are returned. Purely alphabetical words (common in code comments)
    are skipped to reduce false positives.
    """
    tokens = _TOKENIZER_PATTERN.split(content)
    flagged: list[tuple[str, float]] = []

    for token in tokens:
        token = token.strip("'\"`)\\")
        if len(token) < MIN_TOKEN_LEN:
            continue
        if not _NON_TRIVIAL_PATTERN.search(token):
            continue
        entropy = shannon_entropy(token)
        if entropy >= HIGH_ENTROPY_THRESHOLD:
            flagged.append((token, entropy))

    return flagged


def redact_high_entropy(content: str) -> tuple[str, int]:
    """Replace over-threshold tokens with :data:`HIGH_ENTROPY_MARKER`.

    Returns the redacted content and the total count of redactions made.
    """
    flagged = scan_high_entropy_tokens(content)
    if not flagged:
        return content, 0

    redacted = content
    count = 0
    seen: set[str] = set()
    for token, _ in flagged:
        if token in seen:
            continue
        seen.add(token)
        # Use word-boundary when safe, plain replace otherwise.
        try:
            pattern = re.compile(re.escape(token))
            new_content, n = pattern.subn(HIGH_ENTROPY_MARKER, redacted)
            if n > 0:
                redacted = new_content
                count += n
        except re.error:
            if token in redacted:
                redacted = redacted.replace(token, HIGH_ENTROPY_MARKER)
                count += 1

    return redacted, count
