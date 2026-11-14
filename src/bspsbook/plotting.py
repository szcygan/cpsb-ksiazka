"""Wspólne ustawienia i zapis osobnych figur ilościowych."""
from pathlib import Path
import re
import matplotlib.pyplot as plt


def configure_plots(chapter=4):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelsize": 10, "axes.titlesize": 11,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.22,
        "legend.fontsize": 8, "legend.framealpha": 0.95,
        "figure.dpi": 110, "savefig.dpi": 180,
        "svg.hashsalt": f"CPSB-ch{chapter:02d}-v01", "svg.fonttype": "none",
        "axes.prop_cycle": plt.cycler(color=["#176A8A", "#B25324", "#25805D", "#765390", "#727272"]),
    })


def save_figure(fig, directory, stem):
    """PNG do podglądu i SVG do późniejszego składu; bez danych base64."""
    match = re.match(r"fig_(\d{2})_", stem)
    if match is None:
        raise ValueError("Nazwa figury musi zawierać numer rozdziału: fig_XX_...")
    chapter = int(match.group(1))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{stem}.png", bbox_inches="tight", metadata={"Software": f"CPSB ch{chapter:02d}"})
    fig.savefig(directory / f"{stem}.svg", bbox_inches="tight", metadata={"Date": None, "Creator": f"CPSB ch{chapter:02d}"})
    plt.close(fig)
    print(f"Figura: figures/generated/{stem}.png (+ SVG)")
