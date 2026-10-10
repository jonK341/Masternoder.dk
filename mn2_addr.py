"""Pure-stdlib MN2 address utilities (base58check, P2PKH version byte 43 / prefix 'J').

No external crypto dependencies -- the production server has none installed, and
address *validation* only needs hashing, which hashlib provides. Confirmed in the
prior session: MN2 P2PKH version byte = 43 (0x2B), base58 prefix 'J'.
"""
import hashlib

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MN2_PUBKEY_VERSION = 43  # 0x2B


def b58encode(payload: bytes) -> str:
    n = int.from_bytes(payload, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = 0
    for byte in payload:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + out


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        idx = B58.find(ch)
        if idx < 0:
            raise ValueError(f"invalid base58 char: {ch!r}")
        n = n * 58 + idx
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = 0
    for ch in s:
        if ch == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + full


def hash160_to_address(h160: bytes, version: int = MN2_PUBKEY_VERSION) -> str:
    if len(h160) != 20:
        raise ValueError("hash160 must be 20 bytes")
    payload = bytes([version]) + h160
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return b58encode(payload + checksum)


def address_to_hash160(addr: str) -> bytes:
    raw = b58decode(addr)
    if len(raw) != 25:
        raise ValueError(f"decoded length {len(raw)} != 25")
    payload, checksum = raw[:21], raw[21:]
    calc = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if calc != checksum:
        raise ValueError("bad checksum")
    return payload[1:]


def validate_address(addr: str, version: int = MN2_PUBKEY_VERSION) -> bool:
    """True iff addr is a well-formed base58check MN2 P2PKH address with the right version byte."""
    if not isinstance(addr, str) or not (26 <= len(addr) <= 35):
        return False
    try:
        raw = b58decode(addr)
    except Exception:
        return False
    if len(raw) != 25:
        return False
    payload, checksum = raw[:21], raw[21:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        return False
    return payload[0] == version


if __name__ == "__main__":
    # self-test: round-trip a hash160 through encode/decode/validate
    sample_h160 = bytes(range(20))
    a = hash160_to_address(sample_h160)
    assert a.startswith("J"), a
    assert address_to_hash160(a) == sample_h160
    assert validate_address(a)
    assert not validate_address(a[:-1] + ("x" if a[-1] != "x" else "y"))
    print("mn2_addr self-test OK; sample address =", a)
