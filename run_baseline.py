import os
from datetime import datetime
import yaml
import pandas as pd

from model.model import CrimeABM


def safe_float(x) -> str:
    # 0.55 -> 0p55 (safe for filenames)
    s = f"{float(x):.3f}".rstrip("0").rstrip(".")
    return s.replace(".", "p")


def build_filename(params: dict, ts: str) -> str:
    # include a small set of key params in filename (you can expand later)
    n = params.get("n_agents")
    fc = params.get("forensic_capacity")
    cc = params.get("coercive_capacity")
    det = params.get("detention_days_mean")
    evw = params.get("evidence_window_days")
    m = params.get("sf_m")

    parts = [
        ts,
        f"n{n}",
        f"m{m}",
        f"fc{safe_float(fc)}",
        f"cc{safe_float(cc)}",
        f"det{det}",
        f"evw{evw}",
    ]
    return "__".join(parts) + ".csv"


def main():
    # Load config
    with open("config.yml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    sim_cfg = cfg["simulation"]
    model_cfg = cfg["model"]

    # Flatten rewiring nested config
    rew = model_cfg.get("rewiring", {})
    model_cfg = dict(model_cfg)  # copy
    model_cfg["rewiring_enabled"] = bool(rew.get("enabled", True))
    model_cfg["drop_lawful_edge_prob"] = float(rew.get("drop_lawful_edge_prob", 0.20))
    model_cfg["add_criminal_edge_prob"] = float(rew.get("add_criminal_edge_prob", 0.25))
    model_cfg["max_new_edges_per_event"] = int(rew.get("max_new_edges_per_event", 3))
    model_cfg.pop("rewiring", None)

    # Build model
    model = CrimeABM(
        seed=int(sim_cfg["seed"]),
        **model_cfg
    )

    n_days = int(sim_cfg["n_days"])
    for _ in range(n_days):
        model.step()

    df = model.datacollector.get_model_vars_dataframe()
    df.insert(0, "day", range(1, len(df) + 1))

    # Ensure output dir
    out_dir = os.path.join("experiments")
    os.makedirs(out_dir, exist_ok=True)

    # Timestamp in Sao Paulo local time assumed by your environment; using naive local time
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = build_filename(model_cfg, ts)
    out_path = os.path.join(out_dir, fname)

    # Save CSV
    df.to_csv(out_path, index=False)

    # Also save a companion YAML with the exact params used (highly recommended)
    params_path = out_path.replace(".csv", ".yml")
    with open(params_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"simulation": sim_cfg, "model": cfg["model"]}, f, sort_keys=False)

    print(f"Saved results to: {out_path}")
    print(f"Saved params to:   {params_path}")


if __name__ == "__main__":
    main()
