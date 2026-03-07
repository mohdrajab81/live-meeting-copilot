# Dual Mode Setup Guide

Dual mode captures two independent audio channels simultaneously:

- **Local channel** — your microphone (what you say)
- **Remote channel** — the meeting audio feed (what the other participants say)

Use this mode when you need speaker-separated transcription in a Teams, Zoom, or Google Meet call.
If you only need single-microphone capture, this guide is not required.

---

## Choose Your Speech Engine First

Dual-mode setup depends on which speech engine you choose in **Settings → Capture → Speech Engine**.

### Azure Speech (Stable)

- Uses two recording devices.
- **Usually requires VB-CABLE or another virtual audio cable** so the remote meeting audio appears as a separate input device.

### Nova-3 (Preview)

- Uses your default Windows microphone for the local side.
- Uses built-in Windows **WASAPI loopback** for the remote side.
- **Does not require VB-CABLE or similar routing software.**
- Requires `NOVA3_API_KEY` in `.env`.

---

## Path A — Azure Dual Mode

### Requirements

- **VB-CABLE Virtual Audio Device** — free, download from <https://vb-audio.com/Cable/>
- A physical microphone (USB or built-in) for the local channel

### Step 1 — Install VB-CABLE

1. Download the installer from <https://vb-audio.com/Cable/>.
2. Extract the zip and run `VBCABLE_Setup_x64.exe` as administrator.
3. Restart Windows when prompted.
4. Confirm the two new audio devices appear:
   - `CABLE Input (VB-Audio Virtual Cable)` — playback device
   - `CABLE Output (VB-Audio Virtual Cable)` — recording device

### Step 2 — Route Meeting Audio Through VB-CABLE

In Teams, Zoom, Google Meet, or a similar app, set the speaker output to:

```text
CABLE Input (VB-Audio Virtual Cable)
```

The app plays audio to `CABLE Input`, and Live Meeting Copilot reads it from `CABLE Output`.

### Step 3 — Configure Live Meeting Copilot

Open **Settings** and set:

| Setting | Value |
| --- | --- |
| Speech Engine | `Azure Speech (Stable)` |
| Capture mode | `dual` |
| Local input device | Your physical microphone |
| Remote input device | `CABLE Output (VB-Audio Virtual Cable)` |

Save the settings.

### Step 4 — Validate Azure Dual Mode

1. Start a session.
2. Speak into your microphone — only the local transcript should update.
3. Play or receive meeting audio — only the remote transcript should update.
4. If both channels update from the same source, the routing is incorrect.

---

## Path B — Nova-3 Preview Dual Mode

### Requirements

- Windows 10 or Windows 11
- A normal local microphone
- `NOVA3_API_KEY` in `.env`

### Step 1 — Create Your Nova Key

1. Sign in to the Deepgram Console.
2. Select your project.
3. Open **Settings → API Keys**.
4. Create a key and copy the secret immediately.
5. Add it to `.env`:

```env
NOVA3_API_KEY=<your deepgram api key>
```

### Step 2 — Set Windows Default Devices

Because the current Nova preview path uses default devices directly, confirm:

- your **default input device** is the microphone you want for the local channel
- your **default playback/output device** is the speaker or headset playing remote meeting audio

### Step 3 — Configure Live Meeting Copilot

Open **Settings** and set:

| Setting | Value |
| --- | --- |
| Speech Engine | `Nova-3 (Preview)` |
| Capture mode | `dual` |

Then save the settings.

> In the current Nova preview path, the app uses default mic + default WASAPI loopback. It does not depend on Azure-style manual remote/local device routing.

### Step 4 — Validate Nova Dual Mode

1. Start a session.
2. Speak into your microphone — the local transcript should update.
3. Play or receive meeting audio through your default speakers/headset — the remote transcript should update.
4. No VB-CABLE, Voicemeeter, or similar virtual-routing tool is required for this path.

---

## Common Issues

### Azure dual mode: you cannot hear remote speakers

Because meeting audio is routed to the virtual cable instead of your headset, you will not hear remote participants without an additional step.

**Option A — Windows Listen mode** (simple, works for most setups):

1. Right-click the speaker icon in the Windows taskbar and select **Sound settings**.
2. Scroll down and click **More sound settings** to open the legacy Sound control panel.
3. Go to the **Recording** tab.
4. Right-click `CABLE Output (VB-Audio Virtual Cable)` and select **Properties**.
5. Click the **Listen** tab.
6. Tick **Listen to this device** and select your normal headset or speakers from the **Playback through this device** drop-down.
7. Click **OK**.

**Option B — Voicemeeter** (recommended for production use, lower latency):

1. Download Voicemeeter from <https://vb-audio.com/Voicemeeter/> (free, same developer as VB-CABLE).
2. Configure Voicemeeter to receive audio from `CABLE Output` and send it to both your headset and `CABLE Input` simultaneously.
3. This lets you hear remote participants on your headset while the application reads from a clean, unmodified virtual cable feed.

---

### Local and remote channels bleed into each other

Acoustic feedback or Windows audio enhancement features can cause one channel to appear in the other.

**Mitigations:**

1. Open **Sound settings** → **More sound settings**.
2. For your microphone: select it → **Properties** → **Enhancements** tab → disable all enhancements.
3. For `CABLE Output` in Azure dual mode: select it → **Properties** → **Enhancements** tab → disable all enhancements.
4. Use a headset rather than open speakers to reduce acoustic feedback from the room.
5. In Azure dual mode, always select explicit device IDs — avoid the default-device entries, which can change silently after Windows updates or hardware changes.
6. In Nova preview dual mode, confirm Windows default playback/output still points to the device carrying remote meeting audio.

---

## Application-Level Suppression

The application includes a built-in local-channel suppression window that activates briefly after recent remote audio activity. This reduces residual bleed in common setups but is not a substitute for correct audio routing.

---

## Production Recommendations

- In Azure dual mode, always use explicit device IDs. Do not use the default device entries.
- In Nova preview dual mode, verify the Windows default mic and default playback devices before starting a session.
- Save your settings in the application after selecting devices.
- After Windows updates, driver updates, or docking station changes, re-open Settings and verify your device assignments are still correct.
- If the application log shows repeated "recognition restart" or "buffer overflow" messages on an idle channel, this is normal recovery behaviour — the other channel continues uninterrupted.

---

## Related Documents

- [`INSTALL.md`](../INSTALL.md) — install and run the application
- [`docs/AZURE_PROVISIONING.md`](AZURE_PROVISIONING.md) — Azure credentials setup
