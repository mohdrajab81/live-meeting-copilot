# Azure Provisioning Guide

This guide walks you through creating the Azure resources needed to run
Live Meeting Copilot. Steps 1–2 are **required**. Steps 3–7 are
**optional** (translation override, AI coach, topic tracking, and session summary).

See also:
- `docs/QUICK_START_GUIDE.md`
- `docs/SYSTEM_DEFINITION.md`
- `docs/DUAL_MODE_SETUP.md`

---

## Step 1 — Azure account

If you don't have one: https://azure.microsoft.com/free
Free offers and quotas vary by region and can change over time.

---

## Step 2 — Create an Azure AI Services resource (for Speech)

This gives you the `SPEECH_KEY` and `SPEECH_REGION`.

1. Go to https://portal.azure.com
2. Search for **Azure AI Services** → click **Create**.
3. Fill in:
   - **Subscription**: your subscription
   - **Resource group**: create new, e.g. `rg-meeting-copilot`
   - **Region**: pick one close to you (e.g. `East US`, `West Europe`)
   - **Name**: e.g. `meeting-copilot-speech`
   - **Pricing tier**: `S0`
4. Click **Review + Create** → **Create**.
5. Once deployed, open the resource → **Keys and Endpoint** (left menu).
6. Copy **Key 1** → this is your `SPEECH_KEY`.
7. Note the **Location** (e.g. `eastus`) → this is your `SPEECH_REGION`.

Put these in your `.env`:
```
SPEECH_KEY=<Key 1>
SPEECH_REGION=<location, e.g. eastus>
```

> **Tip**: Use the same resource group for everything in this guide so you
> can delete it all at once when you're done testing.

---

## Step 3 — (Optional) Azure Translator resource

Required only if you want live EN→AR translation. If translation is not needed, skip this step.

1. In the Azure portal, search **Translator** → **Create**.
2. Same resource group and region as above.
3. Pricing tier: `S1` (or `F0` if available for low-volume trials).
4. After deployment → **Keys and Endpoint** → copy **Key 1** and **Location**.

```
TRANSLATOR_KEY=<Key 1>
TRANSLATOR_REGION=<location>
TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
```

---

## Step 4 — Create an Azure AI Foundry project (for coach / topics / summary)

1. Go to https://ai.azure.com
2. Click **New project**.
3. Choose or create an **AI hub** (a hub is a shared compute container):
   - Region: same as your Speech resource.
   - Name: e.g. `meeting-copilot-hub`
4. Project name: e.g. `meeting-copilot`
5. Click **Create**.
6. Once the project is open, copy the **Project endpoint** from the
   overview page. It looks like:
   ```
   https://<hub-name>.services.ai.azure.com/api/projects/<project-name>
   ```
   This is your `PROJECT_ENDPOINT`.

```
PROJECT_ENDPOINT=https://<hub-name>.services.ai.azure.com/api/projects/<project-name>
```

---

## Step 5 — Deploy a model

1. Inside your AI Foundry project, go to **Models + endpoints** → **Deploy model**.
2. Search for **gpt-4.1-mini** → **Deploy**.
3. Deployment name: `gpt-4.1-mini` (keep the default).
4. Click **Deploy**.

```
MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
```

---

## Step 6 — Create agents

You need up to three agents. All are created the same way:

1. Inside your AI Foundry project, go to **Agents** (left menu).
2. Click **New agent**.
3. Set the **Model** to `gpt-4.1-mini` (the deployment you just created).
4. Give it a name and system instructions (see below for each agent).
5. Click **Create**. Copy the **Agent ID** (starts with `asst_`).

### Coach agent (`AGENT_ID`)

**Name**: `Conversation Coach`

**System instructions**:
```
You are an expert real-time communication coach. The user will send recent
transcript excerpts from a live meeting or conversation. Respond with concise,
actionable coaching hints in 1-3 bullet points. Focus on what the local speaker
could say or do better right now. Be direct. Do not repeat what was already said.
```

```
AGENT_ID=asst_<coach agent id>
```

### Topic tracker agent (`TOPIC_AGENT_ID`)

**Name**: `Topic Tracker`

**System instructions**:
```
You are a meeting topic analyzer. The user will send you a recent transcript
excerpt and a list of predefined topic definitions. Identify which topics are
being discussed and estimate the time spent on each. Return a JSON object
with topic labels and coverage status. Be precise and concise.
```
Note:
- This is a baseline only. Actual response shape/constraints are enforced by code-authored request context.

```
TOPIC_AGENT_ID=asst_<topic agent id>
```

### Summary agent (`SUMMARY_AGENT_ID`)

**Name**: `Meeting Summarizer`

**System instructions**:
```
You are a meeting intelligence analyst. Follow the caller-provided output schema exactly.
Return only valid JSON in the requested structure.
Do not add markdown or free-form prose outside the JSON object.
```

```
SUMMARY_AGENT_ID=asst_<summary agent id>
```

---

## Step 7 — Authenticate locally

The app uses `DefaultAzureCredential` to talk to AI Foundry agents.
Run this once (requires [Azure CLI](https://aka.ms/install-azure-cli)):

```powershell
az login
```

If you have multiple tenants / subscriptions:
```powershell
az login --tenant "<your-tenant-id>"
az account set --subscription "<your-subscription-id>"
```
If token scope issues appear with AI Foundry access, re-run with:
```powershell
az login --tenant "<your-tenant-id>" --scope "https://ai.azure.com/.default"
```

---

## Complete .env reference

```
# Required — Speech
SPEECH_KEY=
SPEECH_REGION=eastus

# Optional — Translator
TRANSLATOR_KEY=
TRANSLATOR_REGION=eastus
TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
TRANSLATION_COST_PER_MILLION_USD=10.0

# Optional — AI Foundry (coach / topics / summary)
PROJECT_ENDPOINT=https://<hub>.services.ai.azure.com/api/projects/<project>
MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_AI_PROJECT_ENDPOINT=
AZURE_AI_MODEL_DEPLOYMENT_NAME=

# Coach agent
AGENT_ID=asst_...
AGENT_NAME=

# Topic tracker agent
TOPIC_MODEL_DEPLOYMENT_NAME=
TOPIC_AGENT_ID=asst_...
TOPIC_AGENT_NAME=

# Summary agent
SUMMARY_MODEL_DEPLOYMENT_NAME=
SUMMARY_AGENT_ID=asst_...
SUMMARY_AGENT_NAME=

# Optional auth
API_AUTH_TOKEN=
```

---

## Estimated cost (guideline)

| Feature | Typical cost |
|---|---|
| Speech recognition (S0) | ~`$1.00` per hour per active recognizer |
| Translator (S1) | `~$10` per 1M characters (about `$0.50` per ~50k chars) |
| GPT-4.1-mini (coach + topics + summary) | typically low vs speech cost, usage-dependent |

You can disable translation, coach, and/or topics individually in the app UI
to reduce cost during testing.

---

## Cleanup

Delete the resource group `rg-meeting-copilot` in the Azure portal to remove
all billed resources at once.
