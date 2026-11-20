"""Base62 conversion for non-negative integer identifiers."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(n: int) -> str:
    if type(n) is not int:
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return ALPHABET[0]

    encoded = []
    while n:
        n, remainder = divmod(n, BASE)
        encoded.append(ALPHABET[remainder])
    return "".join(reversed(encoded))


def decode(s: str) -> int:
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if not s:
        raise ValueError("s must not be empty")

    value = 0
    for character in s:
        digit = ALPHABET.find(character)
        if digit == -1:
            raise ValueError(f"invalid base62 character: {character!r}")
        value = value * BASE + digit
    return value


encode_base62 = encode
decode_base62 = decode
