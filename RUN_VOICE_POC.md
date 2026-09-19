# Running the Voice POC in Terminal

## 1. Open PowerShell

Open PowerShell in the project/repository directory.

## 2. Activate the Project Environment

```powershell
.\scripts\activate_project.ps1
```

Wait until the terminal shows:

```text
Environment ready.
```

## 3. Start the Voice POC

```powershell
python -m src.voice.live_call
```

The terminal will start the voice call.

Speak when the terminal shows:

```text
Listening...
```

The agent will respond through the speakers and continue through the Energy journey.

## 4. Stop the Voice POC

Press:

```text
Ctrl+C
```
