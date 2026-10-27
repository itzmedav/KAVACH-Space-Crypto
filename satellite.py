import socket, json, time, base64, os
import oqs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from colorama import init, Fore, Style
init(autoreset=True)

def s(m): print(f"{Fore.BLUE}[SAT]{Style.RESET_ALL} {m}")
def ok(m): print(f"{Fore.GREEN}[SAT]{Style.RESET_ALL} {m}")
def warn(m): print(f"{Fore.RED}[SAT]{Style.RESET_ALL} {m}")

# Pick algorithm supported by liboqs
KEM_ALG = "ML-KEM-768" if "ML-KEM-768" in oqs.get_enabled_kem_mechanisms() else "Kyber768"

def main():
    s("Booting KAVACH Satellite...")
    s(f"Post-Quantum Engine: {KEM_ALG} (NIST FIPS 203)")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('localhost', 9999))
    srv.listen(1)
    s("Waiting for ground station on port 9999...")
    conn, _ = srv.accept()
    ok("Ground station connected!")

    conn.send(b"KAVACH_HELLO\n")
    r = conn.recv(1024).decode().strip()
    if r != "KAVACH_ACK":
        return

    # --- REAL POST-QUANTUM KEY EXCHANGE ---
    s(f"Generating {KEM_ALG} keypair...")
    with oqs.KeyEncapsulation(KEM_ALG) as kem:
        public_key = kem.generate_keypair()
        secret_key = kem.export_secret_key()
        s(f"Public key generated: {len(public_key)} bytes")

        conn.send(b"PK:" + base64.b64encode(public_key) + b"\n")
        s("Public key sent to ground station")

        ct_line = conn.recv(8192).decode().strip()
        ciphertext = base64.b64decode(ct_line.split("CT:")[1])
        s(f"Ciphertext received: {len(ciphertext)} bytes")

        shared_secret = kem.decap_secret(ciphertext)
        ok(f"Shared secret derived: {shared_secret[:8].hex()}...")

    conn.send(b"KAVACH_DONE\n")
    ok(f"{KEM_ALG} KEY EXCHANGE COMPLETE!")
    ok("Quantum-safe encryption channel ACTIVE")

    aes = AESGCM(shared_secret)
    nc = [0]

    s("Waiting for encrypted commands...\n")

    while True:
        try:
            data = conn.recv(8192).decode().strip()
            if not data or data == "QUIT":
                break
            if data.startswith("ENC:"):
                raw = base64.b64decode(data[4:])
                nonce, ct = raw[:12], raw[12:]
                try:
                    cmd = aes.decrypt(nonce, ct, None).decode()
                    s(f"Command: {Fore.CYAN}{cmd}{Style.RESET_ALL}")
                    if "TELEMETRY" in cmd:
                        resp = json.dumps({
                            "temp_c": 22.4, "battery_v": 3.31, "signal_dbm": -42,
                            "crypto": f"{KEM_ALG} + AES-256-GCM",
                            "standard": "NIST FIPS 203 (Aug 2024)",
                            "status": "QUANTUM-SAFE"
                        })
                    elif "STATUS" in cmd:
                        resp = f"ALL NOMINAL | {KEM_ALG} ACTIVE | QUANTUM THREATS: 0"
                    elif "PING" in cmd:
                        resp = f"PONG | {time.time():.3f} | quantum-safe"
                    else:
                        resp = f"ACK:{cmd}"
                    nc[0] += 1
                    n = nc[0].to_bytes(12, 'big')
                    e = aes.encrypt(n, resp.encode(), None)
                    conn.send(b"ENC:" + base64.b64encode(n + e) + b"\n")
                    ok("Encrypted response sent")
                except:
                    warn("DECRYPTION FAILED - TAMPERING DETECTED")
            elif data.startswith("CMD:"):
                warn(f"REJECTED unencrypted command: {data}")
                conn.send(b"REJECTED:KAVACH requires AES-256-GCM\n")
        except:
            break
    conn.close()
    srv.close()
    s("Shutdown complete.")

if __name__ == "__main__":
    main()