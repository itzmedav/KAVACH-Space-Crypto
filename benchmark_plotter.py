import matplotlib.pyplot as plt
import numpy as np

# Empirical Benchmark Data
algorithms = ['RSA-2048\n(Classical)', 'X25519\n(ECC)', 'ML-KEM-768\n(KAVACH PQC)']
keygen_ms = [25.92, 0.11, 0.17]
encap_ms = [0.15, 0.05, 0.19]
pubkey_bytes = [270, 32, 1184]
ciphertext_bytes = [256, 32, 1088]

# Set Matplotlib Styling
plt.style.use('dark_background')
colors = ['#ef4444', '#f59e0b', '#00ffcc']

# Chart 1: Cryptographic Latency (KeyGen vs Encapsulation)
fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
x = np.arange(len(algorithms))
width = 0.35

rects1 = ax1.bar(x - width/2, keygen_ms, width, label='Key Generation (ms)', color='#3b82f6')
rects2 = ax1.bar(x + width/2, encap_ms, width, label='Encap/Enc (ms)', color='#00ffcc')

ax1.set_ylabel('Execution Time (milliseconds)', fontsize=12, fontweight='bold', color='#e0e6ed')
ax1.set_title('KAVACH Latency Comparison: ML-KEM-768 vs Classical Algorithms', fontsize=14, fontweight='bold', pad=15, color='#00ffcc')
ax1.set_xticks(x)
ax1.set_xticklabels(algorithms, fontsize=11, fontweight='bold')
ax1.legend(frameon=True, facecolor='#161e2e', edgecolor='#334155')
ax1.set_yscale('log') # Log scale to handle RSA-2048 25.92ms vs 0.11ms
ax1.grid(axis='y', linestyle='--', alpha=0.3)

# Add Data Labels
for rect in rects1 + rects2:
    height = rect.get_height()
    ax1.annotate(f'{height:.2f} ms',
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),  # 3 points vertical offset
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9, fontweight='bold', color='#ffffff')

plt.tight_layout()
plt.savefig('kavach_benchmark_latency.png', dpi=300)
print("[SUCCESS] Saved high-resolution 300 DPI chart: kavach_benchmark_latency.png")

# Chart 2: Public Key & Network Overhead Comparison
fig2, ax2 = plt.subplots(figsize=(9, 5), dpi=300)

rects3 = ax2.bar(x - width/2, pubkey_bytes, width, label='Public Key Size (Bytes)', color='#8b5cf6')
rects4 = ax2.bar(x + width/2, ciphertext_bytes, width, label='Ciphertext Size (Bytes)', color='#f59e0b')

ax2.set_ylabel('Network Overhead (Bytes)', fontsize=12, fontweight='bold', color='#e0e6ed')
ax2.set_title('KAVACH Data Size Overhead: CCSDS Frame Payload Requirements', fontsize=14, fontweight='bold', pad=15, color='#8b5cf6')
ax2.set_xticks(x)
ax2.set_xticklabels(algorithms, fontsize=11, fontweight='bold')
ax2.legend(frameon=True, facecolor='#161e2e', edgecolor='#334155')
ax2.grid(axis='y', linestyle='--', alpha=0.3)

for rect in rects3 + rects4:
    height = rect.get_height()
    ax2.annotate(f'{int(height)} B',
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9, fontweight='bold', color='#ffffff')

plt.tight_layout()
plt.savefig('kavach_benchmark_overhead.png', dpi=300)
print("[SUCCESS] Saved high-resolution 300 DPI chart: kavach_benchmark_overhead.png")
