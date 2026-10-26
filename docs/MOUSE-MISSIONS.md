# Mouse Missions

Open Mouse Missions from the desktop. Tap picture blocks to programme Mouse:
forward moves one square; left/right turn on the spot. Tap a plus to insert
a block and tap a block to remove it. Run animates the programme; One step
executes a single action. Reset keeps the programme. Hints show the early route.
A wall collision bounces Mouse back and highlights the faulty instruction.

| Levels | Skills |
| --- | --- |
| 1–10 | Steps, turns, sequences and a first repair. |
| 11–19 | Extra corners, zigzags, starting direction and three programmes to fix. |
| 20–27 | Debugging, collecting keys and cheese, and opening doors. |
| 28–36 | If cheese is here, if the path is clear, and if carrying a key. |
| 37–45 | If/otherwise, looking left, repairing and combining decisions. |

Conditional missions run the same programme in different visible gardens.
Questions have tick and, later, cross branches. There are no loops or nested
questions in this version. Every three completed missions offers an equipment
choice until all twelve ranks are earned. Replaying never grants another reward.
Use the collection to combine any earned outfit, gadget and magic ranks.

Programmes and progress save locally. Updates from the original 36-level version
preserve earned equipment and move old mission references after level 10 by nine.
The inserted practice starts incomplete. Back up before updating; downgrading
across this curriculum change requires restoring the matching old database too.

All prompts are bundled. To regenerate them, install the optional speech
dependencies and run `python build_mouse_audio.py --model /path/to/voice.onnx`.
Reduced-motion preferences use static collision feedback. No timer or lost lives.
