# Dual Mode Setup (Mic + Remote Channel)

Use this when you want speaker-separated transcript lines:
- local speaker (you)
- remote speaker (meeting audio)

## Goal
- `local_input_device_id` captures your physical microphone.
- `remote_input_device_id` captures the remote meeting audio feed.

## Recommended routing with VB-CABLE
1. Install VB-CABLE (VB-Audio Virtual Cable).
2. In your meeting app (Teams/Zoom/Meet), set **speaker output** to:
   - `CABLE Input (VB-Audio Virtual Cable)`
3. In Live Meeting Copilot Settings panel:
   - Set Capture Mode to `Dual`
   - Set `local_input_device_id` to your physical microphone
   - Set `remote_input_device_id` to `CABLE Output (VB-Audio Virtual Cable)` (recording side)

Important:
- The meeting app plays audio to **CABLE Input** (playback endpoint).
- The copilot should listen from **CABLE Output** (recording endpoint).
- Device labels can vary by driver/version; pick the endpoint that carries remote audio.

## Two major field issues (and fixes)

### 1) "I cannot hear the remote side from my speakers"
When meeting output is moved to `CABLE Input`, remote audio may no longer play on your speakers/headset.

Fix options:
1. Windows monitor path (quick):
   - Open **Sound Control Panel** -> **Recording** -> `CABLE Output` -> **Properties** -> **Listen**
   - Enable **Listen to this device**
   - Choose your speakers/headset as playback device
2. Mixer path (cleaner):
   - Use Voicemeeter (or similar) to route remote audio to both:
     - `CABLE Input` (for capture)
     - your speakers/headset (for listening)

### 2) "Bleeding/echo between channels"
We observed local/remote bleed that was reduced by disabling advanced audio processing.

Recommended mitigation:
1. Disable Windows **Audio Enhancements/Effects** on:
   - local microphone device
   - virtual cable endpoints
   - speaker/headset output (if processing is enabled)
2. Use headset when possible (reduces speaker-to-mic leakage).
3. Keep explicit device IDs in dual mode (avoid auto/default switching).

## Built-in bleed protection in the app
- The app has a built-in local-channel suppression window of ~1.6s after remote speech activity.
- This reduces echo/bleed even when Windows routing is imperfect.
- Audio-enhancement changes in Windows reduce bleed before it reaches the app; suppression handles residual overlap.

## First validation checklist
1. Start a session.
2. Speak locally: only local speaker lines should appear.
3. Play remote audio: only remote speaker lines should appear.
4. If both appear on one channel, fix audio routing before production use.

## Strongly recommended settings
- Avoid `default` devices in dual mode.
- Select explicit device IDs for both channels.
- Save config after selecting devices.

## Common issues
- No remote text appears:
  - meeting app is not routed to `CABLE Input`, or wrong remote input endpoint selected.
- Both sides appear in local channel:
  - speaker bleed or wrong Windows routing; follow the bleed mitigation section above.
- Intermittent remote capture:
  - another app changed the default audio device; reselect explicit IDs.
- Log message: "Restarting recognition after buffer overflow":
  - this is expected during long idle periods on one channel; the app auto-restarts that channel.
  - the other channel continues running.
