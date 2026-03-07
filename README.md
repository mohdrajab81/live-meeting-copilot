# Live Meeting Copilot

A Windows application for real-time meeting transcription, live English-to-Arabic translation, and AI-powered meeting intelligence.

---

## Quick Start (2 Minutes)

1. Copy `.env.example` to `.env` and set your Azure values.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

For full setup, see [`INSTALL.md`](INSTALL.md) and [`docs/QUICK_START_GUIDE.md`](docs/QUICK_START_GUIDE.md).

---

## Demo

Add a 60-90 second demo clip here for recruiters and reviewers:

- `docs/demo/live-meeting-copilot-demo.mp4` (or `.gif`)

---

## What It Does

| Feature | Requires |
|---|---|
| Real-time speech transcription (English, multiple accents) | Azure AI Services key |
| Live English-to-Arabic translation | Azure AI Services key |
| AI coaching suggestions | Azure AI Foundry (optional) |
| Agenda definitions and adherence in summary output | Azure AI Foundry (optional) |
| Structured meeting summary generation | Azure AI Foundry (optional) |

The application runs entirely on your local machine. No cloud hosting is required.

---

## Getting Started

**Step 1 — Install and run the application**
→ Read [`INSTALL.md`](INSTALL.md)

**Step 2 — Create your Azure credentials**
→ Read [`docs/AZURE_PROVISIONING.md`](docs/AZURE_PROVISIONING.md)

**Already have your Azure key and want the fastest path?**
→ Read [`docs/QUICK_START_GUIDE.md`](docs/QUICK_START_GUIDE.md)

---

## Documentation Index

| Document | Purpose |
|---|---|
| [`INSTALL.md`](INSTALL.md) | Complete installation guide — all three package types |
| [`docs/QUICK_START_GUIDE.md`](docs/QUICK_START_GUIDE.md) | Get to a working session in 10 minutes |
| [`docs/AZURE_PROVISIONING.md`](docs/AZURE_PROVISIONING.md) | Create Azure resources and credentials (beginner-friendly) |
| [`docs/DUAL_MODE_SETUP.md`](docs/DUAL_MODE_SETUP.md) | Capture local and remote speakers separately |
| `docs/BUILD_GUIDE.md` | Build distributable packages — repository only, not included in packages |
| `docs/SYSTEM_DEFINITION.md` | Architecture and agent model — repository only, not included in packages |

---

## Azure Services at a Glance

The application uses two independent Azure services:

**Azure AI Services** — required
- Provides speech transcription and Arabic translation
- Authenticated with a key and region (set in `.env`)
- Covered in `docs/AZURE_PROVISIONING.md` — Section 2

**Azure AI Foundry** — optional (AI features only)
- Provides coaching suggestions and meeting summaries
- Authenticated via Azure CLI login
- Covered in `docs/AZURE_PROVISIONING.md` — Sections 3 through 5

You can use the transcription and translation features without any Foundry setup.

---

## Minimum Configuration

```env
AZURE_AI_SERVICES_KEY=<your key>
AZURE_AI_SERVICES_REGION=<your region>
```

See [`docs/AZURE_PROVISIONING.md`](docs/AZURE_PROVISIONING.md) for how to obtain these values.

Optional runtime settings template:

```powershell
Copy-Item .\web_translator_settings.example.json .\web_translator_settings.json
```

## Speech Engine Options

The application supports two speech engines:

- **Azure Speech (default)** — uses your `AZURE_AI_SERVICES_KEY` and `AZURE_AI_SERVICES_REGION`.
- **Nova-3 preview** — uses `NOVA3_API_KEY`, which you create in the Deepgram Console for your Deepgram project.

For the current dual-speaker setup:

- **Azure dual mode** usually requires a virtual audio cable such as VB-CABLE so remote meeting audio appears as a separate recording device.
- **Nova-3 preview dual mode** uses Windows WASAPI loopback for the remote side and does **not** require VB-CABLE or similar routing software.

See `INSTALL.md` for the Nova API key variable and `docs/DUAL_MODE_SETUP.md` for the engine-specific dual-mode setup paths.

---

## Package Types

Three pre-built package formats are available:

| Package | File | Installation Requires | Runtime Requires |
| --- | --- | --- | --- |
| Online | `live-meeting-copilot-deploy.zip` | Python 3.10+, internet | Internet (Azure services) |
| Offline | `live-meeting-copilot-offline.zip` | Python 3.10+, no internet | Internet (Azure services) |
| EXE | `live-meeting-copilot-exe.zip` | Nothing | Internet (Azure services) |

> **All three packages require an internet connection during use** to reach Azure Speech,
> Translator, and AI Foundry services. "No internet needed" refers to the installation
> step only, not runtime.

See [`INSTALL.md`](INSTALL.md) for installation steps for each package type.
