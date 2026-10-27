import math
import time
from ccsds import MLKEM768Simulator, CCSDSHelper, SlidingWindowAntiReplay

class SatelliteNode:
    def __init__(self, name: str, apid_base: int, sub_orbit_phase: float, alt_km: float = 500.0):
        self.name = name
        self.apid_base = apid_base
        self.sub_orbit_phase = sub_orbit_phase
        self.alt_km = alt_km
        self.pqc_sim = MLKEM768Simulator()
        self.pk, self.sk = self.pqc_sim.generate_keypair()
        self.shared_key = None
        self.anti_replay = SlidingWindowAntiReplay(window_size=64)
        self.state = "NOMINAL"
        self.lat = 0.0
        self.lon = 0.0

    def update_position(self, epoch_sec: float):
        orbital_period_sec = 5700.0
        omega = (2 * math.pi) / orbital_period_sec
        angle = omega * epoch_sec + self.sub_orbit_phase
        self.lat = 51.6 * math.sin(angle)
        self.lon = math.degrees(omega * epoch_sec * 0.5 + self.sub_orbit_phase) % 360.0 - 180.0

class ConstellationManager:
    def __init__(self):
        self.satellites = {
            "Alpha": SatelliteNode("KAVACH-Alpha", 0x100, 0.0, 500.0),
            "Beta": SatelliteNode("KAVACH-Beta", 0x200, math.radians(15.0), 505.0),
            "Gamma": SatelliteNode("KAVACH-Gamma", 0x300, math.radians(30.0), 495.0)
        }
        self.isl_keys = {}
        self.is_isl_established = False

    def update_orbit_positions(self, epoch_sec: float = None):
        if epoch_sec is None:
            epoch_sec = time.time() % 5700.0
        for sat in self.satellites.values():
            sat.update_position(epoch_sec)

    def establish_isl_handshake(self):
        start_t = time.perf_counter()
        alpha = self.satellites["Alpha"]
        beta = self.satellites["Beta"]
        gamma = self.satellites["Gamma"]

        ct_ab, sec_ab = alpha.pqc_sim.encapsulate(beta.pk)
        key_ab = beta.pqc_sim.decapsulate(ct_ab, beta.sk)

        ct_bg, sec_bg = beta.pqc_sim.encapsulate(gamma.pk)
        key_bg = gamma.pqc_sim.decapsulate(ct_bg, gamma.sk)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        self.isl_keys["Alpha-Beta"] = key_ab
        self.isl_keys["Beta-Gamma"] = key_bg
        self.is_isl_established = True

        return {
            "handshake_status": "SUCCESS",
            "elapsed_ms": round(elapsed_ms, 3),
            "isl_links": [
                {"pair": "KAVACH-Alpha <-> KAVACH-Beta", "pqc_scheme": "ML-KEM-768", "ct_len": len(ct_ab)},
                {"pair": "KAVACH-Beta <-> KAVACH-Gamma", "pqc_scheme": "ML-KEM-768", "ct_len": len(ct_bg)}
            ]
        }

    def calculate_isl_ranges(self):
        self.update_orbit_positions()
        a = self.satellites["Alpha"]
        b = self.satellites["Beta"]
        g = self.satellites["Gamma"]

        def get_dist(s1, s2):
            r1 = 6371.0 + s1.alt_km
            r2 = 6371.0 + s2.alt_km
            dlat = math.radians(s2.lat - s1.lat)
            dlon = math.radians(s2.lon - s1.lon)
            val = math.sin(dlat/2)**2 + math.cos(math.radians(s1.lat)) * math.cos(math.radians(s2.lat)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(val), math.sqrt(1 - val))
            avg_r = (r1 + r2) / 2.0
            return avg_r * c

        dist_ab = get_dist(a, b)
        dist_bg = get_dist(b, g)

        return {
            "Alpha-Beta_km": round(dist_ab, 2),
            "Beta-Gamma_km": round(dist_bg, 2),
            "Alpha-Gamma_km": round(dist_ab + dist_bg, 2)
        }

if __name__ == '__main__':
    cm = ConstellationManager()
    cm.update_orbit_positions()
    res = cm.establish_isl_handshake()
    print("ISL Handshake:", res)
