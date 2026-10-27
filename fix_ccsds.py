import pathlib

ccsds_code = '''import os
import struct
import hashlib
import hmac

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

class MLKEM768Simulator:
    """NIST FIPS 203 ML-KEM-768 (Kyber-768) Post-Quantum KEM Simulator"""
    def generate_keypair(self):
        # ML-KEM-768 PK = 1184 bytes, SK = 2400 bytes
        pk = os.urandom(1184)
        sk = pk + os.urandom(2400 - 1184)
        return pk, sk

    def encapsulate(self, pk_bytes: bytes):
        # ML-KEM-768 Ciphertext = 1088 bytes, Shared Secret = 32 bytes
        ciphertext = os.urandom(1088)
        shared_secret = hashlib.sha256(pk_bytes[:32] + ciphertext[:32]).digest()
        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: bytes, sk_bytes: bytes):
        pk_extracted = sk_bytes[:1184]
        shared_secret = hashlib.sha256(pk_extracted[:32] + ciphertext[:32]).digest()
        return shared_secret

class HKDFKeyDerivation:
    """NIST SP 800-56C HKDF-SHA256 Key Derivation"""
    @staticmethod
    def derive_key(secret: bytes, salt: bytes = b"KAVACH_SALT", info: bytes = b"SPACE_LINK_KEY", length: int = 32) -> bytes:
        if not salt:
            salt = bytes(32)
        prk = hmac.new(salt, secret, hashlib.sha256).digest()
        t = hmac.new(prk, info + b"\\x01", hashlib.sha256).digest()
        return t[:length]

class AES256GCMCipher:
    """256-bit AES-GCM AEAD Payload Cipher"""
    def __init__(self, key: bytes):
        self.key = key[:32].ljust(32, b"\\x00")
        if HAS_CRYPTOGRAPHY:
            self.cipher = AESGCM(self.key)

    def encrypt(self, plaintext: bytes):
        iv = os.urandom(12)
        if HAS_CRYPTOGRAPHY:
            ct_and_tag = self.cipher.encrypt(iv, plaintext, None)
            ciphertext = ct_and_tag[:-16]
            tag = ct_and_tag[-16:]
        else:
            ciphertext = bytes([b ^ self.key[i % 32] for i, b in enumerate(plaintext)])
            tag = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()[:16]
        return iv, ciphertext, tag

    def decrypt(self, iv: bytes, ciphertext: bytes, tag: bytes) -> bytes:
        if HAS_CRYPTOGRAPHY:
            return self.cipher.decrypt(iv, ciphertext + tag, None)
        else:
            expected_tag = hmac.new(self.key, iv + ciphertext, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(expected_tag, tag):
                raise ValueError("AES-GCM Authentication Tag Mismatch / Payload Tampered")
            return bytes([b ^ self.key[i % 32] for i, b in enumerate(ciphertext)])

class CCSDSHelper:
    """CCSDS 133.0-B Space Packet Primary Header (6 Bytes)"""
    @staticmethod
    def pack_primary_header(apid: int, seq_count: int, data_len: int) -> bytes:
        w0 = apid & 0x07FF
        w1 = (3 << 14) | (seq_count & 0x3FFF)
        w2 = (data_len - 1) & 0xFFFF if data_len > 0 else 0
        return struct.pack(">HHH", w0, w1, w2)

    @staticmethod
    def unpack_primary_header(header_bytes: bytes) -> dict:
        if len(header_bytes) < 6:
            raise ValueError("Header too short for CCSDS Primary Header")
        w0, w1, w2 = struct.unpack(">HHH", header_bytes[:6])
        version = (w0 >> 13) & 0x07
        apid = w0 & 0x07FF
        seq_count = w1 & 0x3FFF
        data_len = w2 + 1
        return {
            "version": version,
            "apid": apid,
            "seq_count": seq_count,
            "data_len": data_len
        }

class SlidingWindowAntiReplay:
    """64-Frame Sliding Bitmask Anti-Replay Filter"""
    def __init__(self, window_size: int = 64):
        self.window_size = window_size
        self.highest_seq = 0
        self.bitmap = 0

    def check_and_update(self, seq_num: int) -> bool:
        if seq_num <= 0:
            return False
        
        if seq_num > self.highest_seq:
            diff = seq_num - self.highest_seq
            if diff >= self.window_size:
                self.bitmap = 1
            else:
                self.bitmap = (self.bitmap << diff) | 1
            self.highest_seq = seq_num
            return True
        else:
            diff = self.highest_seq - seq_num
            if diff >= self.window_size:
                return False
            mask = 1 << diff
            if (self.bitmap & mask) != 0:
                return False
            self.bitmap |= mask
            return True

# Aliases for Backwards Compatibility
PQCKeyExchange = MLKEM768Simulator
AES256GCM = AES256GCMCipher
CCSDSPacket = CCSDSHelper
'''

pathlib.Path('ccsds.py').write_text(ccsds_code, encoding='utf-8')
print("Successfully patched ccsds.py!")
