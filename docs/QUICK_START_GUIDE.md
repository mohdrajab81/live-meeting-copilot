# Quick Start Guide

## 1) Install locally
From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you received the offline package (`live-meeting-copilot-offline.zip`), run `setup.ps1`.
It auto-installs dependencies from local `wheelhouse/` without internet.

## 2) Configure environment
Create `.env` from `.env.example` and set at least:

```env
SPEECH_KEY=...
SPEECH_REGION=eastus
```

Optional AI features require:

```env
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
AGENT_ID=asst_...
TOPIC_AGENT_ID=asst_...
SUMMARY_AGENT_ID=asst_...
```
Optional translation config:

```env
TRANSLATOR_KEY=...
TRANSLATOR_REGION=eastus
TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
```

For full Azure setup, see [AZURE_PROVISIONING.md](./AZURE_PROVISIONING.md).

## 3) Run

Recommended (operator path):

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Developer/manual alternative:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:
- `http://127.0.0.1:8000/`

## 4) First-run smoke test
1. Click `Start`, speak for 20-30 seconds, confirm transcript lines appear.
2. In Settings, toggle `Enable Arabic Translation`, save, and verify Arabic column behavior.
3. Open `Topics`, configure at least one definition, run `Analyze now`.
4. Open `Summary`, click `Generate Now`, verify sections and topic coverage render.
5. Export transcript CSV and test `From File` summary.

## 5) Dual mode (local + remote separation)
If you run dual-channel capture, follow:
- [DUAL_MODE_SETUP.md](./DUAL_MODE_SETUP.md)

## 6) Instruction ownership (important)
- Baseline agent instructions: Azure Foundry.
- Runtime coach custom instruction: Settings UI (`coach_instruction`).
- Topic/summary request framing: code-owned templates.

Reference: [SYSTEM_DEFINITION.md](./SYSTEM_DEFINITION.md).

## 7) Optional: EXE distribution for testers
If you want testers to run without installing Python, use:
- [EXE_DISTRIBUTION.md](./EXE_DISTRIBUTION.md)
