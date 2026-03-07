# Build Guide

> **Maintainer document.** This guide is for developers and maintainers who need to build
> distributable packages from the repository. End users do not need this document.

---

## Package Types

Three distributable formats can be built from the repository:

| Package | Output File | Installation Requires | Runtime Requires |
| --- | --- | --- | --- |
| Online | `dist/live-meeting-copilot-deploy.zip` | Python 3.10+, internet | Internet (Azure services) |
| Offline | `dist/live-meeting-copilot-offline.zip` | Python 3.10+, no internet | Internet (Azure services) |
| EXE | `dist/live-meeting-copilot-exe.zip` | Nothing | Internet (Azure services) |

> "No internet required" refers to the installation step only. All three packages call Azure
> Speech, Translator, and AI Foundry over the network at runtime.

All build commands are run from the repository root.

---

## Build: Online Package

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-deployment-package.ps1
```

**Output:** `dist/live-meeting-copilot-deploy.zip`

### Contents

| Item | Description |
| --- | --- |
| `app/` | Application source code |
| `static/` | Web frontend files |
| `README.md` | Product overview and documentation index |
| `INSTALL.md` | Installation guide |
| `requirements.txt` | Python dependency list |
| `requirements-nova3.txt` | Optional Nova-3 preview dependency list |
| `.env.example` | Environment variable template |
| `web_translator_settings.example.json` | Safe runtime settings template |
| `setup.ps1` | First-time setup script |
| `run.ps1` | Application start script |
| `docs/QUICK_START_GUIDE.md` | 10-minute quick start |
| `docs/AZURE_PROVISIONING.md` | Azure account and resource setup |
| `docs/DUAL_MODE_SETUP.md` | Dual-speaker audio routing |

---

## Build: Offline Package

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-offline-package.ps1
```

**Output:** `dist/live-meeting-copilot-offline.zip`

### Contents

Same as the online package, plus:

| Item | Description |
| --- | --- |
| `wheelhouse/` | Pre-downloaded Python dependency wheels |

The build machine needs internet access once to download the wheels into `wheelhouse/`, including the optional Nova-3 preview wheels referenced by `requirements-nova3.txt`.
The target machine does not need internet access at any point.

---

## Build: EXE Package

The EXE package produces a self-contained Windows executable compiled by [Nuitka](https://nuitka.net/).
No Python installation is required on the target machine.

### Build Machine Requirements

- Python 3.10 or later
- Nuitka:

  ```powershell
  python -m pip install nuitka
  ```

- Microsoft Visual C++ Build Tools (required by Nuitka for compilation; part of Visual Studio or the standalone Build Tools installer)
- Optional for Nova-3 preview in the EXE: install `requirements-nova3.txt` into the build environment before running the build script

### Build Command

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-nuitka-package.ps1
```

The first run downloads and compiles the Nuitka C backend, which can take several minutes.
The `.build` cache in `dist/_nuitka_build/` is preserved between runs, so subsequent builds are significantly faster.

**Optional — also keep the compiled `.dist` folder after zipping (for troubleshooting):**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-nuitka-package.ps1 -KeepBuildDir
```

**Output:** `dist/live-meeting-copilot-exe.zip`

### Contents

| Item | Description |
| --- | --- |
| `live-meeting-copilot.exe` | Standalone compiled executable |
| *(compiled runtime)* | Nuitka-bundled Python runtime and dependencies |
| `static/` | Web frontend files |
| `README.md` | Product overview and documentation index |
| `INSTALL.md` | Installation guide |
| `.env.example` | Environment variable template |
| `web_translator_settings.example.json` | Safe runtime settings template |
| `docs/QUICK_START_GUIDE.md` | 10-minute quick start |
| `docs/AZURE_PROVISIONING.md` | Azure account and resource setup |
| `docs/DUAL_MODE_SETUP.md` | Dual-speaker audio routing |

### Build Notes

- The script preserves Nuitka's `.build` cache in `dist/_nuitka_build/`, which speeds up repeated builds significantly.
- Rebuilds can still take time because Nuitka must re-scan modules, refresh generated code for changed dependencies, and recreate the final zip.
- If source files or bundled dependencies changed, only part of the compile can be reused; the first build after large changes will still be noticeably slower.
- The following large scientific packages are excluded from the EXE to reduce output size: `pandas`, `matplotlib`, `scipy`, `sklearn`, `IPython`, `jupyter`.
- If `deepgram` and `pyaudiowpatch` are available in the build environment, the EXE bundles Nova-3 preview support. Otherwise selecting Nova in the app falls back to Azure at runtime.
- The EXE is Windows-only. The build machine must also be Windows.
- The entry point compiled into the EXE is `app_launcher.py`.

---

## What Is Excluded from All Packages

| Excluded | Reason |
| --- | --- |
| `.env` | Contains secrets — must remain local to each user's machine |
| `web_translator_settings.json` | Contains local device IDs and personal runtime settings |
| `docs/BUILD_GUIDE.md` | Maintainer document — not relevant to end users |
| `docs/SYSTEM_DEFINITION.md` | Developer document — not relevant to end users |
| `.venv/` | Not portable — each user runs `setup.ps1` to create their own |
| `dist/` | Build output directory — not part of source |
| `tests/` | Not needed at runtime |
| `scripts/` | Build scripts — not needed at runtime |
