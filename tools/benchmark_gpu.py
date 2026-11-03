#!/usr/bin/env python3
"""Time Eon's published PyTorch backend with this app's sugar inputs."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--eon-code', required=True, type=Path)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--rate', type=float, default=100)
    args = parser.parse_args()
    sys.path.insert(0, str(args.eon_code))
    import pyarrow
    import torch
    from run_pytorch import DT, MODEL_PARAMS, TorchModel

    print(json.dumps({'torch': torch.__version__, 'pyarrow': pyarrow.__version__}), flush=True)
    data = np.load(args.data / 'brain.npz')
    n = len(data['ids'])
    graph = csr_matrix((data['weights'] / 0.275, data['post'], data['ptr']), shape=(n, n))
    graph = graph.transpose().tocsr()
    weights = torch.sparse_csr_tensor(torch.from_numpy(graph.indptr),
                                     torch.from_numpy(graph.indices),
                                     torch.from_numpy(graph.data).float(),
                                     size=graph.shape, device='cuda')
    indices = data['sugar'].tolist()
    model = TorchModel(1, n, DT, MODEL_PARAMS, weights, indices, 'cuda')
    rates = torch.zeros(1, n, device='cuda')
    rates[:, indices] = args.rate
    with torch.no_grad():
        for trial in range(2):
            state = model.state_init()
            torch.cuda.synchronize()
            started = time.perf_counter()
            for _ in range(10000):
                state = model(rates, *state)
            torch.cuda.synchronize()
            print(json.dumps({'backend': 'eon_pytorch_cuda', 'trial': trial,
                              'neurons': n, 'connections': graph.nnz,
                              'sugar_grns': len(indices), 'input_hz': args.rate,
                              'fly_seconds': 1, 'wall_seconds': time.perf_counter() - started,
                              'allocated_vram_mb': torch.cuda.max_memory_allocated() / 1e6}), flush=True)


if __name__ == '__main__':
    main()
