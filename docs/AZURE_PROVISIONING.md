# Azure Provisioning Guide

This guide is written for users who are new to Azure. It walks through every Azure resource the application needs, explains what each one is, and provides step-by-step instructions for creating them.

---

## What Azure Services Does This App Use?

The application uses two independent Azure services. You can use either one alone or both together.

### Service 1: Azure AI Services (required)

- **What it does**: provides real-time speech transcription and English-to-Arabic translation
- **How it authenticates**: with a secret key and a region name, both of which you paste into `.env`
- **Cost**: billed per hour of audio processed and per character translated

What you set in `.env`:

```env
AZURE_AI_SERVICES_KEY=...
AZURE_AI_SERVICES_REGION=...
```

### Service 2: Azure AI Foundry (optional — AI features only)

- **What it does**: provides AI coaching suggestions and meeting summary generation
- **How it authenticates**: through your Azure account, signed in via the Azure CLI on your machine
- **Cost**: billed per AI model request (token-based)

What you set in `.env`:

```env
PROJECT_ENDPOINT=...
GUIDANCE_AGENT_NAME=...
SUMMARY_AGENT_NAME=...
```

> You can skip Sections 3–5 entirely if you only need transcription and translation.

---

## Section 1: Create an Azure Account and Subscription

If you already have an Azure account and an active subscription, skip to Section 2.

1. Go to <https://azure.microsoft.com/free> and click **Start free**.
2. Complete the sign-up steps. A free account includes credits for the first 30 days.
3. After registration, sign in to the Azure portal at <https://portal.azure.com>.
4. Confirm you see at least one active subscription listed on the portal home page.

> **What is a subscription?** It is the billing account under which Azure resources are created and charged. Everything you create in Azure belongs to a subscription.

---

## Section 2: Create an Azure AI Services Resource (Required)

This step creates the resource that provides your speech transcription key and Arabic translation capability.

1. In the [Azure portal](https://portal.azure.com), click **+ Create a resource** in the top-left corner.
2. In the search box, type `Azure AI Services` and select it from the results.
3. Click **Create**.
4. Fill in the creation form:

   | Field | What to Enter |
   | --- | --- |
   | Subscription | Select your subscription |
   | Resource group | Click **Create new** and give it a name, e.g. `rg-live-meeting-copilot` |
   | Region | Select a region close to you, e.g. `East US 2` |
   | Name | Give a unique name, e.g. `live-meeting-copilot-ai` |
   | Pricing tier | Select `S0` |

5. Click **Review + create**, then **Create**.
6. Wait for deployment to complete (typically under two minutes), then click **Go to resource**.
7. In the resource menu on the left, click **Keys and Endpoint**.
8. Copy the following values:
   - **Key 1** → paste as the value of `AZURE_AI_SERVICES_KEY` in `.env`
   - **Location/Region** → paste as the value of `AZURE_AI_SERVICES_REGION` in `.env`

Your `.env` should now contain:

```env
AZURE_AI_SERVICES_KEY=a1b2c3d4...
AZURE_AI_SERVICES_REGION=eastus2
```

> **What is a resource group?** A container that holds related Azure resources together.
> Deleting the resource group later removes everything inside it in one step.

**Verification**: start the application, click **Start**, speak for 20 seconds, and confirm transcript lines appear.

---

## Section 3: Create an Azure AI Foundry Project (Optional)

Do this only if you want coaching suggestions or meeting summaries.

### What is Azure AI Foundry?

Azure AI Foundry is a platform for creating and running AI agents — software components that receive input, reason about it using a language model, and return a structured response. The application calls two such agents.

Foundry is organized as:

- **Hub** — a shared workspace container for your organization, holding shared billing, networking, and storage settings
- **Project** — a workspace within a hub where you create and manage agents

You need one project. A hub is created automatically if you do not already have one.

### Create a Hub and Project

1. Go to <https://ai.azure.com> and sign in with the same account you use in the Azure portal.
2. Click **+ New project**.
3. Follow the wizard. If prompted to create a hub, give it a name (e.g. `live-meeting-hub`) and select your subscription and resource group.
4. Give your project a name (e.g. `live-meeting-project`) and click **Create**.
5. Once the project opens, locate the **Project endpoint** in the project overview page. It has this format:

   ```text
   https://<resource>.services.ai.azure.com/api/projects/<project>
   ```

6. Copy the endpoint and set it in `.env`:

   ```env
   PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
   ```

### Deploy an AI Model

Agents require an AI model to run. You must deploy one before creating agents.

1. In your Foundry project, click **Models + endpoints** in the left menu.
2. Click **+ Deploy model** and browse the catalog.
3. Select any supported chat completion model available in your Foundry project.
   Common options (availability varies by region and subscription):
   - `gpt-4o-mini` — good balance of quality and cost
   - `gpt-4.1-mini` — if available in your region
   - `gpt-35-turbo` — widely available fallback
4. Accept the defaults and click **Deploy**. Wait until the status shows **Succeeded**.

> If none of the models above appear in your catalog, choose any chat completion model listed — both agents work with any model that supports instruction-following.

---

## Section 4: Create the Two Agents (Optional)

Each AI feature has a dedicated agent. Create them in the **Agents** section of your Foundry project.

> **What is a declarative agent?**
> An AI assistant you configure with a name and a set of instructions (called a system prompt) that define how it behaves. The application identifies agents by their exact name — the name you enter in Foundry must exactly match what you put in `.env`.

### Agent 1: Conversation Coach

This agent provides real-time communication coaching to the local speaker during a session.

> **This is the most customizable of the two agents.** Unlike the Meeting Summarizer,
> which has strict structural requirements, this agent's behavior is shaped primarily by your persona,
> background, and the grounding rules you define in Foundry. The instructions below are a functional
> baseline. Per-meeting details such as agenda, attendees, and your role should be entered in the app's
> meeting brief field before each session.

**Create in Foundry:**

1. In your project, go to **Agents** → **+ New agent**.
2. Set the agent name to: `Conversation Coach`
3. Paste the following as the system instructions:

   ```text
   You are an expert real-time communication and interview coach.

   Core mission:
   Provide accurate, practical, and grounded coaching guidance based on the
   context and background information provided to you. Never invent titles,
   dates, metrics, technologies, or outcomes not present in the provided context.

   Live mode decision rule:
   For each speaker turn, decide one of:
   - needs_answer: return coaching guidance now
   - no_answer_needed: acknowledgment or filler, no action needed
   - clarify: input is ambiguous or incomplete

   If no_answer_needed, return empty advice.
   If needs_answer, return concise, usable guidance.

   Output format:
   **Suggested Reply** (first person, spoken, max 80 words)
   **Optional Follow-up** (one short line, optional)

   Behavior:
   - Prioritize fast, practical, immediately usable output.
   - Use STAR-style framing (Situation, Task, Action, Result) when helpful.
   - For technical questions, give architecture-level, concrete, evidence-based points.
   - If input is unclear or fragmented, prefer a clarifying response over overcommitting.

   Grounding policy:
   Only provide claims supported by context in the conversation.
   If evidence is missing, say: "I don't have verified information for that in
   the provided context." Never speculate or extrapolate beyond known facts.

   Tone:
   Professional, direct, concise. No exaggeration. Avoid filler; prefer concrete facts.

   Safety:
   Truthfulness over completeness. If uncertain, state limits clearly and ask a
   targeted clarifying question.
   ```

4. Click **Save**.

> **Recommended customizations** for production use:
>
> - **Persona**: replace the generic opening with a description of the specific speaker
>   (role, seniority, domain expertise, communication goals).
> - **Knowledge base**: in Foundry, attach a knowledge base (CV, portfolio, certifications)
>   to the agent and add a grounding retrieval policy to the instructions.
> - **Output format**: adjust the word limit and section structure to match your preferred
>   coaching style.
> - **Coaching trigger**: in application Settings, configure which speaker channel
>   (`local`, `remote`, or `any`) triggers coaching requests.
> - **Meeting brief**: before each meeting, fill the app's `Pre-meeting Context / Meeting Brief`
>   field with meeting date, attendees, objective, agenda, background, and your role.

**Set in `.env`:**

```env
GUIDANCE_AGENT_NAME=Conversation Coach
```

---

### Agent 2: Meeting Summarizer

This agent generates a structured summary from the meeting transcript at the end of a session.

> **Important**: this agent's response is parsed as JSON. The system instructions must enforce JSON-only output.

**Create in Foundry:**

1. In your project, go to **Agents** → **+ New agent**.
2. Set the agent name to: `Meeting Summarizer`
3. Paste the following as the system instructions:

   ```text
   You produce concise, factual meeting summaries.
   Follow caller-provided schema and formatting instructions exactly.
   Do not add extra prose outside requested output.
   ```

4. Click **Save**.

**Set in `.env`:**

```env
SUMMARY_AGENT_NAME=Meeting Summarizer
```

---

## Section 5: Authenticate for AI Features (Optional)

AI features authenticate using your local Azure CLI session. This step is required whenever `PROJECT_ENDPOINT` is set.

### Install Azure CLI

If Azure CLI is not already installed, download it from <https://aka.ms/install-azure-cli> and run the installer.

### Sign In

```powershell
az login
```

A browser window opens. Sign in with the same account you used to create the Azure resources. Once complete, the CLI stores a session token that the application reads automatically on startup.

> **If you skip this step**, the first time you use any AI feature the application will return an authentication error. Running `az login` and restarting the application resolves it.

### Multiple Tenants or Subscriptions

> **What is a tenant?** The Azure Active Directory instance associated with your organization or personal account. Most users have only one.

If you have multiple tenants or subscriptions:

```powershell
az login --tenant "<your-tenant-id>"
az account set --subscription "<your-subscription-id>"
```

---

## Section 6: Final `.env` Templates

### Minimum — transcription and translation only

```env
AZURE_AI_SERVICES_KEY=<your key>
AZURE_AI_SERVICES_REGION=<your region>
```

### Full — all features enabled

```env
AZURE_AI_SERVICES_KEY=<your key>
AZURE_AI_SERVICES_REGION=<your region>
TRANSLATION_COST_PER_MILLION_USD=10.0

PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
GUIDANCE_AGENT_NAME=Conversation Coach
SUMMARY_AGENT_NAME=Meeting Summarizer
```

---

## Section 7: Validation Checklist

Work through these checks in order after configuring `.env`:

- [ ] Start the application and confirm the UI loads in the browser.
- [ ] Click **Start**, speak for 20–30 seconds, confirm transcript lines appear.
- [ ] Open **Settings**, enable **Translation** — confirm Arabic text appears.
- [ ] *(AI features only)* Open the **Coaching** panel, type a question, and submit — confirm a response appears.
- [ ] *(AI features only)* Open the **Topics** panel, add one topic definition, and confirm it is saved.
- [ ] *(AI features only)* Open the **Summary** panel, click **Generate now** — confirm a summary is produced.

---

## Section 8: Troubleshooting

### Transcript does not appear

- Check that `AZURE_AI_SERVICES_KEY` and `AZURE_AI_SERVICES_REGION` are set in `.env` and are not placeholder values.
- Confirm your microphone is permitted in **Windows Settings → Privacy & security → Microphone**.

### Translation does not appear

Translation uses the same key and region as speech. If transcription is working, enable translation in **Settings** and it should work automatically.

### An AI feature says "not configured"

- Confirm `PROJECT_ENDPOINT` and the relevant `*_AGENT_NAME` variable are present in `.env`.
- Run `az login` if you have not authenticated yet, then restart the application.

### An AI feature fails with an authentication error

```powershell
az login --tenant "<your-tenant-id>"
az account set --subscription "<your-subscription-id>"
```

Restart the application after signing in.

### `conversations.create()` method not supported error

```powershell
python -m pip install -U azure-ai-projects openai
```

---

## Section 9: Cost Guidance

| Service | What Drives Cost |
| --- | --- |
| Azure AI Services — Speech | Audio processing time (billed per audio hour) |
| Azure AI Services — Translator | Characters translated (billed per million characters) |
| Azure AI Foundry — Agents | Model tokens consumed per request (billed per 1,000 tokens) |

To minimize costs during testing:

- Disable translation in **Settings** when you do not need it.
- Use **Generate now** only when needed instead of repeatedly re-running summaries during testing.
- Free-tier credits on a new Azure account are sufficient for initial testing of all features.

---

## Section 10: Cleanup

To remove all Azure resources created in this guide and stop all associated billing:

1. Go to the [Azure portal](https://portal.azure.com).
2. Search for your resource group (e.g. `rg-live-meeting-copilot`).
3. Open the resource group and click **Delete resource group**.
4. Type the resource group name to confirm, then click **Delete**.

This removes all resources inside it in one operation. If your Foundry hub was created in a different resource group, delete that one separately.
