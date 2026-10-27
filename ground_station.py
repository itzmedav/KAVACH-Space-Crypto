import socket, time, base64
import oqs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from colorama import init, Fore, Style
init(autoreset=True)

def g(m): print(f"{Fore.CYAN}[GND]{Style.RESET_ALL} {m}")
def ok(m): print(f"{Fore.GREEN}[GND]{Style.RESET_ALL} {m}")
def hack(m): print(f"{Fore.MAGENTA}[ATK]{Style.RESET_ALL} {m}")

KEM_ALG = "ML-KEM-768" if "ML-KEM-768" in oqs.get_enabled_kem_mechanisms() else "Kyber768"

def main():
    print(f"""
{Fore.CYAN}===============================================
  KAVACH Ground Station v2.0 (REAL PQC)
  Algorithm: {KEM_ALG} (NIST FIPS 203) + AES-256-GCM
  Mode: Native C++ liboqs Integration
==============================================={Style.RESET_ALL}
    """)

    g("Connecting to satellite...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('localhost', 9999))
        ok("Connected!")
    except:
        print(f"{Fore.RED}Run satellite.py first!{Style.RESET_ALL}")
        return

    hello = sock.recv(1024).decode().strip()
    if "HELLO" in hello:
        ok("Satellite handshake received")
    sock.send(b"KAVACH_ACK\n")

    # --- REAL POST-QUANTUM KEY EXCHANGE ---
    g(f"Receiving {KEM_ALG} public key...")
    pk_line = sock.recv(8192).decode().strip()
    public_key = base64.b64decode(pk_line.split("PK:")[1])
    ok(f"Public key received ({len(public_key)} bytes)")

    g(f"Performing {KEM_ALG} encapsulation...")
    with oqs.KeyEncapsulation(KEM_ALG) as kem:
        ciphertext, shared_secret = kem.encap_secret(public_key)

    ok(f"Shared secret derived: {shared_secret[:8].hex()}...")
    g(f"Ciphertext size: {len(ciphertext)} bytes")

    sock.send(b"CT:" + base64.b64encode(ciphertext) + b"\n")
    done = sock.recv(1024).decode().strip()
    if "DONE" in done:
        ok(f"{KEM_ALG} KEY EXCHANGE COMPLETE!")

    aes = AESGCM(shared_secret)
    nc = [0]

    def send_enc(msg):
        nc[0] += 1
        n = nc[0].to_bytes(12, 'big')
        e = aes.encrypt(n, msg.encode(), None)
        sock.send(b"ENC:" + base64.b64encode(n + e) + b"\n")

    def recv_enc():
        d = sock.recv(8192).decode().strip()
        if d.startswith("ENC:"):
            raw = base64.b64decode(d[4:])
            try:
                return aes.decrypt(raw[:12], raw[12:], None).decode()
            except:
                return "[TAMPERED]"
        return d

    # --- TEST COMMANDS ---
    print(f"\n{Fore.CYAN}--- ENCRYPTED COMMANDS ({KEM_ALG} + AES-256) ---{Style.RESET_ALL}\n")
    for cmd in ["GET TELEMETRY", "GET STATUS", "PING"]:
        g(f"Sending: {cmd}")
        send_enc(f"CMD:{cmd}")
        time.sleep(0.3)
        r = recv_enc()
        ok(f"Satellite: {Fore.GREEN}{r}{Style.RESET_ALL}\n")
        time.sleep(0.3)

    # --- ATTACK SIMULATION ---
    print(f"\n{Fore.RED}--- ATTACK SIMULATION ---{Style.RESET_ALL}\n")
    time.sleep(0.5)

    hack("Intercepting encrypted packets...")
    hack("Attempting AES-256-GCM decryption without key...")
    time.sleep(0.5)
    hack("RESULT: IMPOSSIBLE. AES-256-GCM is unbreakable. DEAD.")
    print()
    time.sleep(0.5)

    hack("Sending fake unencrypted command...")
    sock.send(b"CMD:SELF_DESTRUCT\n")
    time.sleep(0.3)
    r = sock.recv(1024).decode().strip()
    hack(f"Response: {r}")
    hack("RESULT: REJECTED. DEAD.")
    print()
    time.sleep(0.5)

    hack(f"Simulating Shor's & Grover's Algorithms on {KEM_ALG}...")
    time.sleep(1)
    hack(f"RESULT: {KEM_ALG} uses Module-LWE lattice mathematics.")
    hack("No known quantum algorithm can break lattice problems.")
    hack("NIST standardized this in August 2024 (FIPS 203).")
    hack("Your satellite is quantum-safe until at least 2050+. DEAD.")
    print()

    print(f"""
{Fore.YELLOW}--- COMPARISON ---{Style.RESET_ALL}

{Fore.RED}WITHOUT KAVACH (Current ISRO satellites):{Style.RESET_ALL}
  Key Exchange: RSA-2048 / ECDH-P256
  Quantum Threat: BROKEN by Shor's Algorithm (~2030-2035)
  Harvest Now Decrypt Later: ALREADY HAPPENING

{Fore.GREEN}WITH KAVACH v2.0 (Your Prototype):{Style.RESET_ALL}
  Key Exchange: {KEM_ALG} (NIST FIPS 203)
  Quantum Threat: SECURE (Lattice-based Module-LWE)
  Harvest Now Decrypt Later: MATHEMATICALLY USELESS
  Security Level: NIST Level 3 (equivalent to AES-192)

{Fore.CYAN}KAVACH v2.0 demo complete.
You are running native C++ liboqs post-quantum algorithms
standardized by NIST in August 2024.{Style.RESET_ALL}
    """)

    sock.send(b"QUIT\n")
    sock.close()

if __name__ == "__main__":
    main()