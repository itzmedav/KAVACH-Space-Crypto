import struct
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def derive_session_keys(shared_secret: bytes, salt: bytes = None):
    """
    NIST SP 800-56C HKDF-SHA256 Key Derivation.
    Derives 32-byte AES-256 key and 32-byte MAC key from ML-KEM shared secret.
    """
    if salt is None:
        salt = b"\x00" * 32
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=salt,
        info=b"KAVACH-LEO-SPACECRAFT-PROTOCOL-V1",
    )
    key_material = hkdf.derive(shared_secret)
    k_enc = key_material[:32]
    k_mac = key_material[32:64]
    return k_enc, k_mac

def pack_ccsds_header(apid: int, seq_count: int, payload_len: int, packet_type: int = 0) -> bytes:
    """Packs a 6-byte CCSDS 133.0-B Primary Header."""
    version = 0
    sec_hdr_flag = 0
    word0 = ((version & 0x07) << 13) | ((packet_type & 0x01) << 12) | ((sec_hdr_flag & 0x01) << 11) | (apid & 0x07FF)
    seq_flags = 3
    word1 = ((seq_flags & 0x03) << 14) | (seq_count & 0x3FFF)
    word2 = max(0, payload_len - 1) & 0xFFFF
    return struct.pack(">HHH", word0, word1, word2)

pack_primary_header = pack_ccsds_header

def unpack_ccsds_header(data: bytes) -> tuple:
    """Unpacks a 6-byte CCSDS 133.0-B Primary Header."""
    if len(data) < 6:
        raise ValueError("Data too short for CCSDS Primary Header")
        
    word0, word1, word2 = struct.unpack(">HHH", data[:6])
    version = (word0 >> 13) & 0x07
    packet_type = (word0 >> 12) & 0x01
    sec_hdr_flag = (word0 >> 11) & 0x01
    apid = word0 & 0x07FF
    seq_flags = (word1 >> 14) & 0x03
    seq_count = word1 & 0x3FFF
    payload_len = word2 + 1
    
    hdr_dict = {
        "version": version,
        "type": packet_type,
        "sec_hdr_flag": sec_hdr_flag,
        "apid": apid,
        "seq_flags": seq_flags,
        "seq": seq_count,
        "len": payload_len
    }
    return hdr_dict, data[6:]

unpack_primary_header = unpack_ccsds_header

def make_telemetry_frame(seq: int, payload: bytes, apid: int = 0x100) -> bytes:
    """Helper to construct a complete CCSDS Telemetry frame."""
    hdr = pack_ccsds_header(apid=apid, seq_count=seq, payload_len=len(payload), packet_type=0)
    return hdr + payload

class CCSDSPacket:
    """CCSDS 133.0-B Space Packet wrapper class."""
    def __init__(self, apid: int, seq_count: int, payload: bytes, packet_type: int = 0):
        self.apid = apid
        self.seq_count = seq_count
        self.payload = payload
        self.packet_type = packet_type

    def pack(self) -> bytes:
        hdr = pack_ccsds_header(self.apid, self.seq_count, len(self.payload), self.packet_type)
        return hdr + self.payload

    def __getitem__(self, key):
        if key == "apid":
            return self.apid
        elif key in ("seq", "seq_count"):
            return self.seq_count
        elif key in ("payload", "data"):
            return self.payload
        elif key in ("type", "packet_type"):
            return self.packet_type
        elif key in ("len", "length"):
            return len(self.payload)
        raise KeyError(f"Invalid key: {key}")

    @classmethod
    def unpack(cls, data: bytes):
        hdr, payload = unpack_ccsds_header(data)
        return cls(apid=hdr["apid"], seq_count=hdr["seq"], payload=payload, packet_type=hdr["type"])

class AntiReplayWindow:
    """64-frame sliding bitmap anti-replay window filter for CCSDS sequence counts."""
    def __init__(self, window_size: int = 64):
        self.window_size = window_size
        self.max_seq = -1
        self.bitmap = 0

    def is_valid(self, seq: int) -> bool:
        if self.max_seq == -1:
            self.max_seq = seq
            self.bitmap = 1
            return True

        if seq > self.max_seq:
            diff = seq - self.max_seq
            if diff >= self.window_size:
                self.bitmap = 1
            else:
                self.bitmap = (self.bitmap << diff) & ((1 << self.window_size) - 1)
                self.bitmap |= 1
            self.max_seq = seq
            return True

        diff = self.max_seq - seq
        if diff >= self.window_size:
            return False

        if (self.bitmap >> diff) & 1:
            return False

        self.bitmap |= (1 << diff)
        return True

    def validate(self, seq: int) -> bool:
        return self.is_valid(seq)

    def validate_and_update(self, seq: int) -> bool:
        return self.is_valid(seq)
