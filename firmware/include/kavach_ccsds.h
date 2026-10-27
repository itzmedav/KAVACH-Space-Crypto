#ifndef KAVACH_CCSDS_H
#define KAVACH_CCSDS_H

#include <Arduino.h>
#include <stdint.h>

// CCSDS Application Process Identifiers (APIDs)
#define APID_HANDSHAKE  0x001
#define APID_TELEMETRY  0x100
#define APID_COMMAND    0x200

// CC1101 SPI Pinout Configuration for ESP32-S3
#define CC1101_CS   10
#define CC1101_GDO0 14
#define CC1101_GDO2 13
#define CC1101_SCK  12
#define CC1101_MISO 11
#define CC1101_MOSI 9

// 6-Byte CCSDS Primary Header (Big-Endian network byte order)
struct __attribute__((packed)) CCSDSHeader {
    uint8_t  version_type_apid1; // Bits 15-13: Ver(000), Bit 12: Type(0/1), Bit 11: SecHdr(0), Bits 10-8: APID high
    uint8_t  apid_low;           // Bits 7-0: APID low
    uint16_t seq_flags_count;    // Bits 15-14: SeqFlags(11), Bits 13-0: SeqCount
    uint16_t packet_length;      // Total bytes - 1
};

// 64-Frame Sliding Anti-Replay Window Filter
class AntiReplayFilter {
private:
    uint16_t max_seq;
    uint64_t window_bitmap;

public:
    AntiReplayFilter() : max_seq(0), window_bitmap(0) {}

    bool validate_sequence(uint16_t seq) {
        if (seq > max_seq) {
            uint16_t diff = seq - max_seq;
            if (diff >= 64) {
                window_bitmap = 1;
            } else {
                window_bitmap = (window_bitmap << diff) | 1;
            }
            max_seq = seq;
            return true;
        }

        uint16_t diff = max_seq - seq;
        if (diff >= 64) {
            return false; // Packet too old (outside 64-frame window)
        }

        if (window_bitmap & (1ULL << diff)) {
            return false; // Replay attack detected (already seen)
        }

        window_bitmap |= (1ULL << diff);
        return true;
    }
};

inline void pack_ccsds_primary(uint8_t* buf, uint16_t apid, uint8_t type, uint16_t seq, uint16_t len) {
    buf[0] = ((type & 0x01) << 4) | ((apid >> 8) & 0x07);
    buf[1] = apid & 0xFF;
    buf[2] = 0xC0 | ((seq >> 8) & 0x3F);
    buf[3] = seq & 0xFF;
    buf[4] = ((len - 1) >> 8) & 0xFF;
    buf[5] = (len - 1) & 0xFF;
}

#endif // KAVACH_CCSDS_H
