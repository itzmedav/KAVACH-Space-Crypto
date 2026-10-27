import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class RFSpectrumAnalyzer:
    """
    Simulates a 433.92 MHz SDR (Software Defined Radio) Spectrum Analyzer & Waterfall.
    Calculates power spectral density (PSD) with Doppler shift and noise floor.
    """
    def __init__(self, num_bins=64, center_freq_mhz=433.92, bandwidth_khz=500, history_depth=30):
        self.num_bins = num_bins
        self.center_freq = center_freq_mhz
        self.bandwidth = bandwidth_khz / 1000.0  # MHz
        self.history_depth = history_depth
        
        # Frequency axis vector
        self.freq_axis = np.linspace(
            self.center_freq - self.bandwidth / 2,
            self.center_freq + self.bandwidth / 2,
            self.num_bins
        )
        
        # Waterfall matrix initialized with noise floor (-110 dBm)
        self.waterfall_matrix = np.full((self.history_depth, self.num_bins), -110.0)

    def update_spectrum(self, doppler_khz=0.0, tx_active=True, rssi_dbm=-75.0, corrupt=False):
        """
        Generates a new RF spectrum line and pushes it into the waterfall matrix.
        """
        # Baseline Gaussian Thermal Noise Floor (-110 dBm +/- 2.5 dB)
        psd = np.random.normal(loc=-110.0, scale=2.5, size=self.num_bins)

        if tx_active:
            # Shift carrier center based on Doppler shift
            carrier_freq = self.center_freq + (doppler_khz / 1000.0)
            
            # Find closest bin index for carrier
            carrier_idx = np.abs(self.freq_axis - carrier_freq).argmin()
            
            # Form GFSK / FSK modulated spectrum peak profile
            peak_power = rssi_dbm
            for i in range(self.num_bins):
                dist = abs(i - carrier_idx)
                if dist == 0:
                    psd[i] = peak_power
                elif dist <= 3:
                    # Sideband roll-off
                    psd[i] = max(psd[i], peak_power - dist * 12.0 + np.random.normal(0, 1.5))
                elif dist <= 6:
                    psd[i] = max(psd[i], peak_power - 36.0 - (dist - 3) * 6.0)

        if corrupt:
            # Add random broadband jammer / noise burst spikes across spectrum
            spike_indices = np.random.choice(self.num_bins, size=5, replace=False)
            psd[spike_indices] = np.random.uniform(-65.0, -45.0, size=5)

        # Roll waterfall matrix and insert newest spectrum line at top
        self.waterfall_matrix = np.roll(self.waterfall_matrix, shift=1, axis=0)
        self.waterfall_matrix[0, :] = psd

        return self.freq_axis, psd

    def generate_plotly_fig(self):
        """
        Creates a combined Plotly figure with Spectrum Analyzer (top) and Waterfall Spectrogram (bottom).
        """
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=("433.92 MHz Real-Time Spectrum Analyzer (PSD)", "2D SDR RF Waterfall Spectrogram")
        )

        current_psd = self.waterfall_matrix[0, :]

        # 1. 2D Spectrum PSD Line Plot
        fig.add_trace(
            go.Scatter(
                x=self.freq_axis,
                y=current_psd,
                mode='lines',
                line=dict(color='#00F0FF', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 240, 255, 0.15)',
                name='Power (dBm)'
            ),
            row=1, col=1
        )

        # Signal marker for carrier peak
        peak_idx = np.argmax(current_psd)
        fig.add_trace(
            go.Scatter(
                x=[self.freq_axis[peak_idx]],
                y=[current_psd[peak_idx]],
                mode='markers+text',
                marker=dict(color='#00FF66', size=8, symbol='triangle-up'),
                text=[f"{current_psd[peak_idx]:.1f} dBm"],
                textposition="top center",
                name="Carrier Peak"
            ),
            row=1, col=1
        )

        # 2. Waterfall Heatmap
        fig.add_trace(
            go.Heatmap(
                z=self.waterfall_matrix,
                x=self.freq_axis,
                colorscale='Viridis',
                zmin=-115.0,
                zmax=-50.0,
                colorbar=dict(title="dBm", len=0.45, y=0.25),
                name="Waterfall"
            ),
            row=2, col=1
        )

        # Dark Aerospace Theme Styling
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#070b12',
            plot_bgcolor='#0b1320',
            margin=dict(l=40, r=40, t=40, b=40),
            height=450,
            showlegend=False,
            font=dict(family="IBM Plex Mono, monospace", color="#8c9ba5")
        )

        fig.update_xaxes(title_text="Frequency (MHz)", row=2, col=1, gridcolor="#1a2638")
        fig.update_yaxes(title_text="Power (dBm)", range=[-120, -30], row=1, col=1, gridcolor="#1a2638")
        fig.update_yaxes(title_text="Time Sweep", row=2, col=1, gridcolor="#1a2638")

        return fig
