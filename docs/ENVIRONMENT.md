# Whole-brain desktop environment

As of 2026-11-03. This is a model-driven taste experiment and an exploratory
olfactory readout, not a validated complete virtual animal.

## Start

On this PC, the model and dependencies have already been prepared:

```sh
cd /home/olle/dev/desktop-fly-linux
./run.sh
```

A fresh clone needs `uv`, system GTK/PyGObject/cairo/Xlib, and:

```sh
./tools/setup-senses.sh
./run.sh --seed 42
```

The setup packs the published model into `~/.cache/desktopfly/v783/brain.npz`
(about 52 MB). `manifest.json` records source hashes and group mappings.
`--sensory-data DIR` selects another prepared cache. `--legacy-sugar` preserves
the old approach-to-sugar demonstration. Installations without the optional
model retain that legacy mode and print an explicit message.

Click Food, Bitter or Smell to spawn an item 80 pixels from the fly. Drag it
onto the fly or elsewhere. Right-click an item to remove it. Ctrl+right-click places
the last selected kind at the pointer. Tray actions place each kind directly.
Reset environment clears all items, resets sensory voltages/spikes and hunger.

## What reacts, and which cells

Food contact activates the 20 available right labellar sugar gustatory receptor
neurons from Shiu's published list at 100 Hz. Bitter contact activates the 20
available bitter GRNs at 200 Hz. Only the mapped **MN9** motor neuron,
FlyWire **720575940660219265**, controls the new feeding permission. A recent
MN9 spike plus food contact permits the existing authored feeding animation.
Removing food or loss of MN9 output ends feeding; escape retains priority.

The full graph contains the paper's intermediate feeding circuitry, including
**G2N-1, FMIn, Fdg, Bract** and other SEZ neurons. These cells are not shortcut
controllers. Nothing directly injects feeding current into MN9, and bitter
has no direct body-level stop flag. Cutting MN9's incoming connections in a
probe eliminates its sugar-driven spikes.

Smell is a generic, modeled plume. It stimulates the **68 ORN_DM1** olfactory
receptor neurons up to 100 Hz. The view displays their measured mean rate and
the response of the **two DM1_lPN** projection neurons, at real coordinates.
There is **no odor-driven steering**. The plume is not calibrated to a named
odorant. This unmodified model can sustain very high DM1_lPN activity after
stimulation; reset between experiments. This is not biological validation of
its olfactory dynamics.

The paper used v630. This implementation uses the authors' public v783 files:
**138,639 neurons**, **15,091,983 directed weighted connections**, representing
**54,492,922 anatomical synapses**. Three paper IDs are absent in v783 and are
explicitly omitted, never guessed or silently remapped:

- Sugar GRN `720575940620900446` (20 of 21 retained).
- Bitter GRN `720575940618600651` (20 of 21 retained).
- Other MN9 `720575940645521262` (one of two retained).

Exact sensory IDs are in `sensory-data/groups.json`; the generated manifest
records missing IDs and all selected group counts. ORN_DM1 and DM1_lPN are
selected by exact Codex v783 primary type annotations.

## Real versus authored

**Measured data:** neuron identities, connectivity, signed synapse-count
weights, and anatomical coordinates. **Simulated:** propagated spikes under
the Shiu LIF equations. **Authored interfaces:** screen contact geometry,
plume shape, conversion to stimulation rates, the 150 ms MN9 readout window,
body geometry, proboscis animation, consumption, satiety and motion mapping.

The original **668-neuron movement circuit** is preserved as an independent
simulation alongside the full-brain sensory model. Its **LC4/LPLC2 →
DNp01/Giant Fiber** escape pathway, cut/restore and bypass, **DNp09** walking,
**MDN** backward walking, **DNa01/DNa02** turning and **DNg11** grooming retain
their existing parameters. The two models are not one integrated neural body.
In full-brain mode, food and odor no longer directly drive steering commands;
legacy sugar attraction is still available with the explicit legacy flag.

Safe on-camera description: “We added the published full-brain model alongside
the desktop fly's movement circuit. Sugar activates taste neurons and feeding
only starts when the simulated MN9 motor neuron fires. Bitter suppresses that
through the wiring. Smell activates real olfactory neurons, but we have not
shown that it steers the fly. The body animation and the sensory interface are
ours.”

## Feasibility and speed

Hardware: Ryzen 5 9600X (6 cores, 12 threads), 60 GiB RAM, RTX 4070 with
12,282 MiB VRAM. At inspection about 20 GiB RAM and 9 GiB VRAM were available.

Two methods were tested on the full graph:

- Eon's published PyTorch CUDA backend: initial 21-GRN/200-Hz trial took
  **5.55–5.70 s per simulated second**. A matched 20-GRN/100-Hz probe took
  **5.91 and 5.97 s**; about **153 MB allocated tensor VRAM**.
- The compiled CPU sparse-event solver: initial 21-GRN/200-Hz trial took
  **0.272 and 0.289 s per simulated second**, after a 0.657 s first call.
  The final 20-GRN/100-Hz taste probes measured **0.21–0.27 s**.

This is the fastest method tested here, not a claim against every GPU engine.
Brian2CUDA was not installed or benchmarked. The new CPU solver keeps all
neurons and connections; cells exactly at rest need no update until receiving
input. Once activated, cells remain in the integration list. Delayed spikes
expand into synaptic updates only when due. No graph pruning or integration
steps are skipped for speed. Equations use exact linear integration, 0.1 ms
steps, 20 ms membrane tau, 5 ms synaptic tau, 2.2 ms refractory period, 1.8 ms
delay, 0.275 mV per signed synapse and the paper's 68.75 mV Poisson input kicks.
All three configured receptor groups retain zero refractory time, including
when their current stimulus is zero. The paper removes refractoriness only
for its configured Poisson targets; this runtime keeps its input groups fixed.

Go for the full model's taste experiment. Strong odor activity costs
**2.85–4.9 wall seconds per fly second**, depending on concurrent desktop load.
A worker runs that neural clock independently so the UI stays responsive.
Input changes coalesce to the newest sample; old stimuli do not accumulate in
a backlog. The displayed speed is measured neural time per wall time, smoothed
across updates. Neural time is slower under expensive odor activity.

## Verification

- Tiny Brian2 parity test: every voltage, synaptic state and spike count
  matched a deterministic four-cell excitation/inhibition/delay/refractory
  probe. Maximum observed state error was approximately 1.4e-14 mV.
- Seed 42, one simulated second: rest **0 MN9 spikes**, sugar **66**, sugar +
  bitter **0**, sugar with MN9 inputs cut **0**. Odor activated ORN_DM1 and
  DM1_lPN without a steering command.
- An independent seed 1234 also passed sugar activation, bitter suppression
  and ORN/PN response checks. This is numerical testing, not a new animal trial.
- 15 unit tests passed, including the tiny solver and motor-permission checks.
  Existing sim invariants and all 21 behavior checks passed. Wheel build passed.
- Invisible KWin/XWayland lab: Food button placement; drag of each item; sugar
  contact → MN9 → extended proboscis; bitter → loss of feeding; walk, moonwalk,
  visual cut, GF bypass, restore, brain movement/rotation and reset passed.
  Screenshots were inspected. Host pointer, focus and clipboard were untouched.

Reproduce:

```sh
./run.sh --sensorytest --seed 42
./run.sh --simtest
./run.sh --behaviortest
.venv-brain/bin/python -m unittest discover -s desktopfly/tests -p 'test_*.py'
```

Brian2 is only needed for the optional parity test:
`uv pip install --python .venv-brain/bin/python brian2==2.11.0`.
Without Brian2/Numba, the small default suite skips that parity check explicitly.

Claude Opus independently re-ran all scientific and behavior checks on the
implementation commit and found no blocking issue. The optional dependency
fallback was corrected afterward: auto-detected caches fall back to legacy
mode when Numba is unavailable; an explicit `--sensory-data` request still
fails with setup instructions. Worker errors now remain resettable, and item
removal uses identity so coincident sources cannot remove one another.

GPU timing uses `tools/benchmark_gpu.py`, Eon's `code/` directory at commit
`a3db62f9436074e485c0278290c2164ed6150808`, and CUDA PyTorch 2.14.1+cu130.
The app's dependency pins are in `sensory-data/requirements.txt`.

Evidence: [machine-readable probes and desktop checks](environment-verification.json).
The magnified views use 3× renderer zoom in the invisible desktop to make the
proboscis easier to inspect; neural and body state are unchanged.
Screenshots: [magnified feeding](img/environment-feeding-detail.png),
[magnified bitter suppression](img/environment-bitter-detail.png),
[feeding](img/environment-feeding.png),
[bitter suppression](img/environment-bitter.png), [odor response](img/environment-odor.png).

## Desktop dragging on Niri

Niri uses a stationary native Wayland layer surface for input. A held item's
preview moves within that surface, preserving the pointer's original grip offset.
Release commits the final position and restores the small input region. KDE/X11
uses the same stationary-input/moving-preview approach with an explicit pointer
grab and a release watchdog. Bitter snaps to Food within 28 logical pixels.
Left press picks up; right-click removes. Item interaction does not inject looming
input into the escape circuit.

[Niri QA](NIRI_QA.md) records the full mouse-driven sweep, screenshots and video.

## Sources

- [Shiu et al., Nature 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11446845/).
- [Authors' model and sensory IDs](https://github.com/philshiu/Drosophila_brain_model/tree/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960).
- [Eon backend comparison](https://github.com/eonsystemspbc/fly-brain/tree/a3db62f9436074e485c0278290c2164ed6150808).

FlyWire-derived model data retain the existing CC BY-NC 4.0 restriction.
