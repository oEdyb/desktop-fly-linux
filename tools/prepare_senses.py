#!/usr/bin/env python3
"""Download the published v783 model and pack its full signed connectivity."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktopfly.simcore.sensory import DEFAULT_DATA

PAPER = "https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960/"
CODEX = "https://storage.googleapis.com/flywire-data/codex/data/fafb/783/"
FILES = {
    "Connectivity_783.parquet": PAPER,
    "Completeness_783.csv": PAPER,
    "classification.csv.gz": CODEX,
    "consolidated_cell_types.csv.gz": CODEX,
    "coordinates.csv.gz": CODEX,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    source = args.source_dir or output / "downloads"
    source.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, base in FILES.items():
        path = source / name
        if not path.exists():
            temp = path.with_suffix(path.suffix + ".partial")
            print(f"Downloading {name}", flush=True)
            urlretrieve(base + name, temp)
            temp.replace(path)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if hashes["Connectivity_783.parquet"] != "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347":
        raise ValueError("Connectivity checksum differs from the published v783 model")
    if hashes["Completeness_783.csv"] != "bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311":
        raise ValueError("Neuron ordering checksum differs from the published v783 model")
    ids = pd.read_csv(source / "Completeness_783.csv", index_col=0).index.to_numpy(np.int64)
    lookup = {str(rid): i for i, rid in enumerate(ids)}
    edges = pd.read_parquet(source / "Connectivity_783.parquet")
    graph = coo_matrix((edges["Excitatory x Connectivity"].to_numpy(np.float64) * 0.275,
                        (edges["Presynaptic_Index"], edges["Postsynaptic_Index"])),
                       shape=(len(ids), len(ids))).tocsr()
    group_path = Path(__file__).resolve().parents[1] / "sensory-data" / "groups.json"
    raw_groups = json.loads(group_path.read_text())
    groups = {}
    missing = {}
    for name in ("sugar", "bitter", "mn9"):
        groups[name] = np.array([lookup[i] for i in raw_groups[name] if i in lookup], np.int32)
        missing[name] = [i for i in raw_groups[name] if i not in lookup]
    classes = pd.read_csv(source / "classification.csv.gz")
    types = pd.read_csv(source / "consolidated_cell_types.csv.gz")
    typed = classes.merge(types, on="root_id")
    for group, cell_type in (("orn", "ORN_DM1"), ("pn", "DM1_lPN")):
        found = typed.loc[typed.primary_type == cell_type, "root_id"]
        groups[group] = np.array([lookup[str(i)] for i in found if str(i) in lookup], np.int32)
    coords = pd.read_csv(source / "coordinates.csv.gz").drop_duplicates("root_id")
    xyz = np.array([list(map(float, str(p).strip("[]").split())) for p in coords.position])
    center = (xyz.min(axis=0) + xyz.max(axis=0)) / 2
    scale = 20 / np.ptp(xyz, axis=0).max()
    normalized = (xyz - center) * scale * [1, -1, -1]
    positions = np.full((len(ids), 3), np.nan, np.float32)
    for rid, pos in zip(coords.root_id, normalized):
        i = lookup.get(str(rid))
        if i is not None:
            positions[i] = pos
    with (output / "brain.partial").open("wb") as file:
        np.savez_compressed(file, ids=ids, positions=positions, ptr=graph.indptr,
                            post=graph.indices, weights=graph.data, **groups)
    (output / "brain.partial").replace(output / "brain.npz")
    manifest = {
        "version": "FlyWire v783", "neurons": len(ids), "connections": graph.nnz,
        "anatomical_synapses": int(edges.Connectivity.sum()),
        "groups": {k: len(v) for k, v in groups.items()},
        "missing_paper_ids": missing, "sha256": hashes,
        "source": PAPER, "groups_source": raw_groups["source"],
        "model": "Shiu 2024; dt 0.1 ms; linear integration; tau_m 20 ms; tau_s 5 ms; delay 1.8 ms; refractory 2.2 ms; weight 0.275 mV",
        "license": "FlyWire-derived data: CC BY-NC 4.0",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"ok": True, "output": str(output), **manifest}, indent=2))


if __name__ == "__main__":
    main()
