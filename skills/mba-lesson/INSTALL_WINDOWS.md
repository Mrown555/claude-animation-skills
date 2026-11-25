# Installing on Windows 11 (WSL2 + Ubuntu 24.04)

Run each stage, check its result, then move on. Nothing here uses Homebrew.

## Stage A: check what you have (PowerShell, read-only)
```powershell
wsl --status
```
```powershell
wsl -l -v
```
```powershell
nvidia-smi
```
If `Ubuntu-24.04` is listed with VERSION 2, skip Stage B.

## Stage B: install WSL2 + Ubuntu 24.04 (admin PowerShell), then reboot
```powershell
wsl --install -d Ubuntu-24.04
```
Create `C:\Users\<you>\.wslconfig` with:
```ini
[wsl2]
memory=8GB
processors=8
swap=8GB
```
```powershell
wsl --shutdown
```
**Check (inside Ubuntu):** `free -g` shows about 8 GB, and `nproc` shows 8.

## Stage C: system packages (Ubuntu terminal)
```bash
sudo apt update && sudo apt install -y ffmpeg python3-venv python3-pip poppler-utils git curl fonts-dejavu-core
```
**Check:** `ffmpeg -version | head -1`, `pdfinfo -v` and `python3 -V` (3.12) all print versions.

## Stage D: Linux Node 22 (only if `which node` is empty or starts with /mnt/c)
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
```
```bash
source ~/.bashrc && nvm install 22
```
**Check:** `which node` shows `/home/<you>/.nvm/...`.

## Stage E: Claude Code inside WSL
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
**Check:** `claude --version`.

## Stage F: the repository (in your Linux home, not /mnt/c)
```bash
git clone <your fork URL> ~/claude-animation-skills
```
```bash
cd ~/claude-animation-skills && git checkout mba-lesson-studio && ./install.sh
```
```bash
bash ~/claude-animation-skills/skills/mba-lesson/setup.sh
```
`install.sh` links all 12 skills (the 11 originals plus `/mba-lesson`) into `~/.claude/skills`. `setup.sh` checks, installs what is missing and ends with "ready".
If Chromium fails to start, run the `install-deps` command that it prints.

## Stage G: smoke test
```bash
cd ~/claude-animation-skills/skills/mba-lesson && bash tests/smoke.sh
```
This builds the bundled test lesson end to end and prints the QC status.

## Daily use
Open Ubuntu, run `claude`, then type `/mba-lesson` and give it the PDF path. Windows files are under `/mnt/c/Users/<you>/...`, so copy the PDF into WSL or give that path.
Finished videos are in `~/MBA-Studio/`. In Windows Explorer, open `\\wsl$\Ubuntu-24.04\home\<you>\MBA-Studio`.
