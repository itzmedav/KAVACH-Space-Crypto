"""
KAVACH CCSDS Space Packet Layer
Simplified standards-inspired CCSDS 133.0-B Primary Header
for post-quantum encrypted satellite TM/TC frames.
"""
import struct

APID_TELEMETRY = 0x100
APID_TELECOMMAND = 0x200
APID_HANDSHAKE = 0x001

class CCSDSPacket:
    def __init__(self, apid: int, seq_count: int, data: bytes, is_telecommand: bool = False):
        self.version = 0
        self.type = 1 if is_telecommand else 0
        self.sec_header_flag = 0
        self.apid = apid & 0x7FF
        self.seq_flags = 0b11
        self.seq_count = seq_count & 0x3FFF
        self.data = data

    def pack(self) -> bytes:
        word0 = ((self.version & 0x7) << 13) | ((self.type & 0x1) << 12) | ((self.sec_header_flag & 0x1) << 11) | (self.apid & 0x7FF)
        word1 = ((self.seq_flags & 0x3) << 14) | (self.seq_count & 0x3FFF)
        length = max(len(self.data) - 1, 0) & 0xFFFF
        header = struct.pack(">HHH", word0, word1, length)
        return header + self.data

    @staticmethod
    def unpack(raw: bytes):
        if len(raw) < 6:
            raise ValueError("CCSDS frame too short")
        word0, word1, length = struct.unpack(">HHH", raw[:6])
        version = (word0 >> 13) & 0x7
        pkt_type = (word0 >> 12) & 0x1
        apid = word0 & 0x7FF
        seq_flags = (word1 >> 14) & 0x3
        seq_count = word1 & 0x3FFF
        data = raw[6:6 + length + 1]
        return {
            "version": version,
            "type": "TC" if pkt_type else "TM",
            "apid": apid,
            "seq_count": seq_count,
            "seq_flags": seq_flags,
            "length": length + 1,
            "data": data,
            "raw_header": raw[:6],
        }

def make_telemetry_frame(seq: int, payload: bytes) -> bytes:
    return CCSDSPacket(APID_TELEMETRY, seq, payload, is_telecommand=False).pack()

def make_telecommand_frame(seq: int, payload: bytes) -> bytes:
    return CCSDSPacket(APID_TELECOMMAND, seq, payload, is_telecommand=True).pack()

def make_handshake_frame(seq: int, payload: bytes) -> bytes:
    return CCSDSPacket(APID_HANDSHAKE, seq, payload, is_telecommand=False).pack()
