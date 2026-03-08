# Live Meeting Copilot — Installation Guide

This guide covers all three ways to install and run the application on Windows.

---

## Choose Your Package

| Package | File | Installation Requires | Runtime Requires |
| --- | --- | --- | --- |
| **Online** | `live-meeting-copilot-deploy.zip` | Python 3.10 or later, internet | Internet (Azure services) |
| **Offline** | `live-meeting-copilot-offline.zip` | Python 3.10 or later, no internet | Internet (Azure services) |
| **EXE** | `live-meeting-copilot-exe.zip` | Nothing | Internet (Azure services) |

> **All three packages require an internet connection during use** to reach Azure Speech,
> Translator, and AI Foundry services. "No internet needed" refers to the installation
> step only — dependencies are bundled, but Azure calls still go over the network.
>
> **Not sure which to use?** Choose the EXE package — it has the fewest installation requirements.

---

## Option A: Online Package

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or later ([download](https://www.python.org/downloads/) — tick **Add Python to PATH** during install)
- Internet connection during setup

### Installation Steps

#### 1. Extract the package

Extract `live-meeting-copilot-deploy.zip` to a local folder, for example:

```text
C:\tools\live-meeting-copilot
```

#### 2. Run setup

Open PowerShell in that folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` automatically:

- Detects and verifies your Python installation
- Creates a virtual environment (`.venv`)
- Downloads and installs all dependencies from the internet
- Installs optional Nova-3 preview dependencies when `requirements-nova3.txt` is included in the package
- Creates `.env` from the built-in template
- Opens `.env` in Notepad and waits for you to save it

#### 3. Fill in your Azure credentials

When Notepad opens, set at minimum:

```env
AZURE_AI_SERVICES_KEY=<your key>
AZURE_AI_SERVICES_REGION=<your region, e.g. eastus>
```

Save the file and close Notepad. Setup completes automatically.

> Do not have these values yet? See `docs/AZURE_PROVISIONING.md`.

#### 4. Start the application

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Your browser opens automatically to `http://localhost:8000`. If it does not open within a few seconds, navigate there manually.

---

## Option B: Offline Package

The offline package is identical to the online package, except that all Python dependencies are pre-bundled in a `wheelhouse/` folder. No internet connection is needed on the target machine.

The `setup.ps1` script automatically detects the `wheelhouse/` folder, installs both the base dependencies and the optional Nova-3 preview wheels when present, and does not download anything. Prerequisites and installation steps are otherwise identical to Option A.

---

## Option C: EXE Package

### EXE Requirements

- Windows 10 or Windows 11
- Microsoft Visual C++ Redistributable 2015–2022

  Most Windows machines already have this installed. If the application fails to start, [download and install it](https://aka.ms/vs/17/release/vc_redist.x64.exe), then try again.

### EXE Installation Steps

#### 1. Extract the EXE package

Extract `live-meeting-copilot-exe.zip` to a local folder, for example:

```text
C:\tools\live-meeting-copilot
```

#### 2. First run — create your configuration

Double-click `live-meeting-copilot.exe`, or run it from PowerShell:

```powershell
.\live-meeting-copilot.exe
```

On first run, if `.env` does not exist, the launcher:

- Creates `.env` from the built-in template automatically
- Opens `.env` in Notepad
- Exits — you must fill in your credentials before running again

#### 3. Configure your Azure credentials

When Notepad opens, set at minimum:

```env
AZURE_AI_SERVICES_KEY=<your key>
AZURE_AI_SERVICES_REGION=<your region, e.g. eastus>
```

Save the file and close Notepad.

> Do not have these values yet? See `docs/AZURE_PROVISIONING.md`.

#### 4. Second run — start the application

Run `live-meeting-copilot.exe` again. Your browser opens automatically to `http://127.0.0.1:8000`.

> **Windows Firewall prompt**: If a firewall dialog appears, click **Allow access**.

### EXE-Specific Settings

These optional environment variables are only available in the EXE package:

| Variable | Default | Description |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | Network interface the server binds to |
| `APP_PORT` | `8000` | Port the server listens on |
| `OPEN_BROWSER` | `1` | Set to `0` to disable automatic browser launch |

---

## Environment Variables Reference

### Required

| Variable | Description |
| --- | --- |
| `AZURE_AI_SERVICES_KEY` | Your Azure AI Services key |
| `AZURE_AI_SERVICES_REGION` | Region for your Azure AI Services resource (e.g., `eastus`) |

### Optional — AI Features

Required only if you want coaching suggestions or meeting summaries.
Both depend on an Azure AI Foundry project and agent configuration.

| Variable | Description |
| --- | --- |
| `PROJECT_ENDPOINT` | Your Foundry project endpoint URL |
| `GUIDANCE_AGENT_NAME` | Name of the agent handling coaching suggestions |
| `SUMMARY_AGENT_NAME` | Name of the agent handling meeting summaries |
| `OPENAI_API_VERSION` | API version used by the optional shadow final translation path |
| `SHADOW_FINAL_TRANSLATION_ENABLED` | Set to `true` to enable a second-pass Arabic patch for committed finals |
| `SHADOW_FINAL_TRANSLATION_MODEL` | Model deployment name used by the optional shadow final translation path |

See `docs/AZURE_PROVISIONING.md` for how to create and name these agents.

### Optional — General

| Variable | Default | Description |
| --- | --- | --- |
| `TRANSLATION_COST_PER_MILLION_USD` | *(not set)* | Used for on-screen cost estimates only; does not affect translation. When not set, no cost estimate is displayed. |
| `NOVA3_API_KEY` | *(empty)* | Optional key for Nova-3 STT preview. Create it in the Deepgram Console under your project **Settings → API Keys**. Python-based installs pull the optional Nova deps from `requirements-nova3.txt` during setup when that file is packaged. The EXE package uses Nova only when those optional deps were bundled by the maintainer; otherwise it auto-falls back to Azure. |

### Optional — Shadow Final Translation

Use this only if you want final Arabic transcript rows to be patched by a second higher-quality translation pass after the initial Azure Translator result.

```env
OPENAI_API_VERSION=2024-10-21
SHADOW_FINAL_TRANSLATION_ENABLED=true
SHADOW_FINAL_TRANSLATION_MODEL=<your model deployment name>
```

Notes:
- this path uses your existing `PROJECT_ENDPOINT`
- the live partial translation path stays unchanged
- if the shadow pass fails, the normal Arabic translation remains in place

### Optional — Nova-3 Preview

Use this only if you want to switch **Settings → Capture → Speech Engine** from Azure to Nova-3.

1. Sign in to the Deepgram Console.
2. Select your Deepgram project.
3. Open **Settings**.
4. Open **API Keys**.
5. Create a new API key and copy the secret immediately.
6. Paste it into `.env`:

```env
NOVA3_API_KEY=<your deepgram api key>
```

> The Deepgram key is separate from Azure. It does not come from the Azure portal or Azure AI Foundry.

### Dual-Mode Routing by Speech Engine

- **Azure dual mode**: usually needs VB-CABLE or a similar virtual audio cable so remote meeting audio can be captured as a separate input device.
- **Nova-3 preview dual mode**: uses Windows WASAPI loopback for the remote side and does **not** require VB-CABLE or similar routing software.

Current Nova preview behavior:

- local channel = default Windows microphone
- remote channel = default Windows speaker/output loopback
- explicit Azure-style local/remote device IDs are not the primary routing model for Nova

---

## Authenticating for AI Features

If you configure `PROJECT_ENDPOINT` and agent names, the application authenticates through your local Azure CLI session.

Install Azure CLI if not already installed: <https://aka.ms/install-azure-cli>

Sign in:

```powershell
az login
```

A browser window opens for you to sign in with the same account used to create the Azure resources.
Once complete, the CLI stores a session token that the application uses automatically.

If you have multiple Azure tenants or subscriptions:

```powershell
az login --tenant "<your-tenant-id>"
az account set --subscription "<your-subscription-id>"
```

---

## Verification Checklist

After the application starts and the browser opens:

1. Click **Start** and speak for 20–30 seconds.
2. Confirm transcript lines appear on screen.
3. Open **Settings**, enable **Translation** — confirm Arabic text appears alongside the transcript.
4. If AI features are configured:
   - **Coaching**: type a question in the guidance box and submit — confirm a response appears.
   - **Topics**: open **Settings → Topics**, add at least one definition, and confirm it is saved.
   - **Summary**: click **Generate now** — confirm a summary is produced.

---

## Troubleshooting

### PowerShell reports "cannot be loaded because running scripts is disabled"

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then retry the command.

### `setup.ps1` reports "Python 3.10+ not found"

Download Python from <https://www.python.org/downloads/>.
During install, tick **Add Python to PATH**, then run `setup.ps1` again.

### `run.ps1` reports "Dependencies not installed"

Run `setup.ps1` first, then retry.

### Transcript does not appear after clicking Start

- Confirm `AZURE_AI_SERVICES_KEY` and `AZURE_AI_SERVICES_REGION` are set in `.env` and are not placeholder values.
- Confirm your microphone is connected and permitted in **Windows Settings → Privacy & security → Microphone**.

### An AI feature panel says "not configured"

- Confirm `PROJECT_ENDPOINT` and the relevant `*_AGENT_NAME` variable are set in `.env`.
- Run `az login` if you have not authenticated yet.

### An AI feature fails with an authentication error

```powershell
az login --tenant "<your-tenant-id>"
az account set --subscription "<your-subscription-id>"
```

Restart the application after logging in.

### `conversations.create()` method not supported error

```powershell
python -m pip install -U azure-ai-projects openai
```

---

## Related Documents

| Document | Purpose |
| --- | --- |
| `docs/AZURE_PROVISIONING.md` | Create Azure resources and obtain credentials |
| `docs/QUICK_START_GUIDE.md` | Fastest path to first working session |
| `docs/DUAL_MODE_SETUP.md` | Capture local and remote speakers separately for Azure or Nova |
| `docs/BUILD_GUIDE.md` | Build distributable packages (maintainers only) |
