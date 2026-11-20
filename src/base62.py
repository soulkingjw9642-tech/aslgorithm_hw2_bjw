"""Base62 conversion for non-negative integer identifiers."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode_base62(value: int) -> str:
    if type(value) is not int:
        raise TypeError("value must be an integer")
    if value < 0:
        raise ValueError("value must be non-negative")
    if value == 0:
        return ALPHABET[0]

    encoded = []
    while value:
        value, remainder = divmod(value, BASE)
        encoded.append(ALPHABET[remainder])
    return "".join(reversed(encoded))


def decode_base62(encoded: str) -> int:
    if not isinstance(encoded, str):
        raise TypeError("encoded value must be a string")
    if not encoded:
        raise ValueError("encoded value must not be empty")

    value = 0
    for character in encoded:
        digit = ALPHABET.find(character)
        if digit == -1:
            raise ValueError(f"invalid base62 character: {character!r}")
        value = value * BASE + digit
    return value
