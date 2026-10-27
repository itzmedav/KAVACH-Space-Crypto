\# KAVACH: A Post-Quantum Encrypted Space Communication Protocol Utilizing NIST FIPS 203 (ML-KEM-768) and CCSDS 133.0-B Framing for Low-Earth Orbit Satellites



\*\*Authors:\*\* D. Macha et al.  

\*\*Affiliation:\*\* Multidisciplinary Aerospace \& Cyber Security Research Group  

\*\*Target Submission:\*\* IEEE Aerospace Conference / IN-SPACe Research Competition / IAC 2026  

\*\*Repository:\*\* https://github.com/itzmedav/KAVACH-Space-Crypto



\---



\## Abstract



Modern satellite telecommand and telemetry (TC/TM) links heavily rely on classical public-key cryptography (RSA-2048, ECDH-P256) for session key exchange. The impending realization of fault-tolerant quantum computing via Shor’s Algorithm will collapse these classical cryptosystems. Furthermore, hostile actors are executing "Harvest Now, Decrypt Later" (HNDL) interception attacks against Low-Earth Orbit (LEO) satellite downlinks. This paper presents \*\*KAVACH\*\*, a lightweight, zero-trust, post-quantum cryptographic protocol specifically tailored for small satellites (CubeSats) and LEO space assets. KAVACH implements the newly finalized \*\*NIST FIPS 203 (ML-KEM-768)\*\* Module-Lattice Key Encapsulation Mechanism coupled with \*\*NIST SP 800-56C HKDF-SHA256\*\* key derivation and \*\*AES-256-GCM\*\* authenticated payload encryption, framed within standard \*\*CCSDS 133.0-B\*\* Space Packets. We demonstrate sub-millisecond key generation latency (\~0.17 ms) and 100% resilience against replay, bit-flip tampering, and command spoofing attacks over simulated sub-GHz RF space links.



\*\*Index Terms\*\*—Post-Quantum Cryptography, ML-KEM-768, CCSDS, LEO Satellite Security, AES-256-GCM, Anti-Replay, CubeSat, NIST FIPS 203.



\---



\## 1. Introduction



Satellite communications are fundamentally vulnerable due to the broadcast nature of RF transmissions in the Ultra-High Frequency (UHF) and S-bands. The standard space link protocols defined by the Consultative Committee for Space Data Systems (CCSDS) historically prioritized low bandwidth overhead over cryptographic authentication.



With the August 2024 finalization of NIST FIPS 203 (`ML-KEM`), post-quantum cryptography (PQC) transitions from theoretical research to mandatory space operational standards. KAVACH addresses three core challenges:



1\. \*\*Quantum Vulnerability:\*\* Protecting against polynomial-time discrete logarithm solvers on quantum hardware.

2\. \*\*Replay \& Command Injection:\*\* Enforcing strict 64-frame sliding anti-replay window filters.

3\. \*\*Computational Constraint:\*\* Operating within the tight power and memory budgets of microcontroller flight hardware (e.g., ESP32-S3 / ARM Cortex-M4).



KAVACH is designed as a drop-in security layer that preserves CCSDS 133.0-B Primary Header compatibility (APIDs `0x001` Handshake, `0x100` TM, `0x200` TC) while adding NIST Level-3 quantum resistance.



\---



\## 2. Mathematical Cryptographic Foundation



\### A. Module-Lattice Learning With Errors (Module-LWE)



ML-KEM-768 operates over polynomial rings $\\mathcal{R}\_q = \\mathbb{Z}\_q\[X]/(X^n + 1)$, where $n = 256$ and $q = 3329$. Security relies on the hardness of finding short vectors in module lattices ($k = 3$).



\*\*Key Generation:\*\*

$$\\mathbf{A} \\in \\mathcal{R}\_q^{k \\times k}, \\quad \\mathbf{s}, \\mathbf{e} \\in \\mathcal{R}\_q^k$$

$$\\mathbf{t} = \\mathbf{A}\\mathbf{s} + \\mathbf{e}$$

$$\\text{Public Key } (pk) = (\\mathbf{t}, \\rho), \\quad \\text{Secret Key } (sk) = \\mathbf{s}$$



\*\*Encapsulation (Ground -> Space):\*\*

$$\\mathbf{u} = \\mathbf{A}^T \\mathbf{r} + \\mathbf{e}\_1, \\quad v = \\mathbf{t}^T \\mathbf{r} + e\_2 + \\lceil \\frac{q}{2} \\rceil m$$

$$\\text{Ciphertext } (c) = (\\mathbf{u}, v), \\quad \\text{Shared Secret } (ss) = \\text{KDF}(m)$$



\*\*Decapsulation (Spacecraft):\*\* Recovers $m'$ from $(c, sk)$ and derives the identical shared secret if the ciphertext is authentic.



\### B. Key Derivation (NIST SP 800-56C)



After ML-KEM produces the 32-byte shared secret $ss$, KAVACH applies HKDF-SHA256:



$$PRK = \\text{HKDF-Extract}(salt, ss)$$

$$K\_{enc} \\| K\_{mac} \\| IV\_{base} = \\text{HKDF-Expand}(PRK, info=\\text{"KAVACH-LEO-v1"}, L=80)$$



Only the AES-256-GCM encryption key ($K\_{enc}$, 32 bytes) is retained for payload AEAD. Session keys are ephemeral per contact pass.



\### C. Authenticated Encryption



Telemetry and telecommand payloads are protected with AES-256-GCM:



$$C, Tag = \\text{AES-256-GCM-Encrypt}(K\_{enc}, IV, AAD=\\text{CCSDS Header}, P)$$



Any bit-flip in ciphertext or header causes GCM tag verification failure -> immediate frame rejection (zero-trust).



\---



\## 3. System Architecture \& CCSDS Integration



```text

+----------------------------------+      UHF / Sub-GHz Link     +----------------------------------+

|         GROUND STATION           | <=========================> |       KAVACH SPACECRAFT          |

|   (Mission Control Dashboard)    |    ML-KEM-768 + AES-256     |  (Flight Software / ESP32-S3)    |

+----------------------------------+                             +----------------------------------+

| - Ephemeral Key Pair Encap       | === Encapsulated CT (c) ==> | - Decapsulates Shared Secret (K) |

| - HKDF-SHA256 Key Derivation     |                             | - HKDF Payload Key Extraction    |

| - CCSDS Telecommand Packaging    | <=== Encrypted Telemetry == | - AES-256-GCM AEAD Tag Verify    |

| - Anti-Replay Window (64-frame)  |                             | - LEO Dynamics + RF Physics      |

| - Streamlit Mission Control UI   |                             | - Auto-reconnect TCP Flight SW   |

+----------------------------------+                             +----------------------------------+

