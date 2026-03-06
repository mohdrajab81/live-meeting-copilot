# Quick Start Guide

Get the application running in approximately 10 minutes using the online package.

> For other package types (offline or EXE), see [`INSTALL.md`](../INSTALL.md).
> For Azure credentials you do not yet have, see [`docs/AZURE_PROVISIONING.md`](AZURE_PROVISIONING.md).

---

## Before You Begin

Confirm you have all of the following:

- Windows 10 or Windows 11
- Python 3.10 or later (run `python --version` in PowerShell to check)
- Your Azure AI Services key and region — see [`docs/AZURE_PROVISIONING.md`](AZURE_PROVISIONING.md) if you need to create them
- The package file: `live-meeting-copilot-deploy.zip`

---

## Step 1 — Extract

Extract `live-meeting-copilot-deploy.zip` to a local folder, for example `C:\tools\live-meeting-copilot`.

---

## Step 2 — Run Setup

Open PowerShell in the extracted folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Setup installs all dependencies, creates `.env` from the template, and opens it in Notepad.

---

## Step 3 — Enter Your Azure Credentials

In Notepad, fill in:

```env
AZURE_AI_SERVICES_KEY=<paste your key here>
AZURE_AI_SERVICES_REGION=<your region, e.g. eastus>
```

Save the file and close Notepad. Setup completes automatically.

---

## Step 4 — Start the Application

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Your browser opens automatically. If it does not, navigate to `http://localhost:8000`.

---

## Step 5 — Confirm It Works

1. Click **Start**.
2. Speak for 20–30 seconds.
3. Confirm transcript lines appear on screen.
4. Open **Settings** and enable **Translation** — confirm Arabic text appears alongside the transcript.

---

## Optional: Enable AI Features

If you have an Azure AI Foundry project set up (see [`docs/AZURE_PROVISIONING.md`](AZURE_PROVISIONING.md) — Sections 3 through 5), add the following to `.env`:

```env
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
GUIDANCE_AGENT_NAME=<your coaching agent name>
SUMMARY_AGENT_NAME=<your summary agent name>
```

Then authenticate with Azure:

```powershell
az login
```

Restart `run.ps1`. The Coaching and Summary panels in the UI become active.

For speech recognition, Azure Speech is the default. A Nova-3 preview option is available in **Settings > Capture > Speech Engine**. In the Python-based packages, `setup.ps1` also installs the optional Nova dependencies from `requirements-nova3.txt` when that file is included in the package. When the Nova runtime is unavailable, the app falls back to Azure automatically.

---

## If Something Goes Wrong

| Symptom | Where to Look |
| --- | --- |
| Setup or install error | `INSTALL.md` — Troubleshooting section |
| Azure key or region error | `docs/AZURE_PROVISIONING.md` — Section 8 |
| Need to capture both local and remote speakers | `docs/DUAL_MODE_SETUP.md` |
