# Desktop interaction verification

2026-11-03. Niri 26.04 (8ed0da4), xwayland-satellite 0.8.3, GTK4 4.24.1,
gtk4-layer-shell 1.3.0. The real session uses Niri. Verification ran the same Niri
binary inside an invisible `agent-lab` desktop, with a native Wayland window
underneath the fly and environment items. No pointer input was sent to the real
session during QA.

The input source was the private compositor's `zwlr_virtual_pointer_v1` mouse:
actual motion and press/release events, rather than calls to application handlers.
Item creation, stimulation, removal and reset used the visible buttons or items.
An observer recorded model/body state alongside each screenshot. Renderer zoom
was 3× for feeding and bitter proof; neurons and body state were unchanged.

Local evidence lives in `artifacts/niri-qa/`: each screenshot has a matching JSON
state snapshot. `results.json` lists every check and its evidence paths.
`artifacts/niri-qa-full.mp4` is the uninterrupted 1920×1080 capture at 8 fps.
`artifacts/niri-qa-full.capture.json` records frame count and actual duration.
The video captures the real private framebuffer; it is not an authored demo.

The sweep covers moving the brain by its move strip; drag-rotation; LC4, LPLC2,
GF, DNp09 and MDN buttons; cursor escape from a grounded state; Cut preventing
cursor takeoff; GF Bypass while Cut remains active; press/mid/drop screenshots
for Food, Bitter and Smell; food-driven MN9 feeding with the proboscis extended;
bitter snapping onto Food and suppressing feeding; ORN_DM1/DM1_lPN odor activity;
rapid zigzag drags across the native Wayland window; right-click removal of each
item; and Reset environment clearing all items and neural state.

The Walk check requires walking with speed above 35, rather than only a DNp09
spike. Moonwalk requires a positive backward timer. Cursor escape begins grounded
and requires a new flight with GF activity. After every drop, moving the cursor
away must leave the item fixed. Near-food Bitter intentionally snaps to the food
center instead of retaining its grip offset.

Scientific limits remain unchanged: odor shows neural activity, not steering.
The paper model can sustain high DM1_lPN activity after odor; reset between
experiments. Native Wayland does not grant unrestricted global cursor tracking:
the app observes its own fly/item surfaces and available XWayland pointer input.
This sweep verifies approaching the visible fly on Niri, not arbitrary input
observation inside every other application.

Automated checks: unit suite including Brian2 parity, `--simtest`, all 21
`--behaviortest` checks, and `--sensorytest --seed 42`. The sensory probe retains
66 MN9 spikes for sugar, zero for sugar+bitter, and zero with MN9 inputs cut.
