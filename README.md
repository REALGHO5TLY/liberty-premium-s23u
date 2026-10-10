# Liberty Premium S23U — GTA IV Android experiment

An experimental patch for [vaduur/LibertyRecompAndroid](https://github.com/vaduur/LibertyRecompAndroid), pinned to upstream commit `4f6ce516eb1cf606dadacaa63c5f63f00f751a55` (0.5.8.1).

## Goals
- Native-feeling right-side swipe-to-look camera with X/Y sensitivity adjustment and invert Y.
- Keep left joystick and face/shoulder buttons, with control-size and opacity adjustment.
- Audio buffering experiment targeting crackle, preserving graphics, traffic, pedestrians and draw distance.
- Build a separate application ID so your existing installed game remains untouched.

## Build
Open **Actions → GTA IV Premium Android APK → Run workflow**. The Windows workflow clones the pinned upstream source, runs `premium_patch/apply.py`, installs dependencies and attempts an Android ARM64 build. On success it publishes **Liberty-Premium-S23U-APK** as an artifact.

The first workflow/build is experimental and may fail due to native build resource/toolchain constraints. A successful compile does **not** verify audio/FPS on the S23 Ultra. No GTA IV game content is included. The new app has separate data and requires its own game installation; keep the existing installation and saves.

## Current scope
This first version changes touch input and a reversible audio buffer setting. It does not implement arbitrary movement of all buttons, a guaranteed sound decoder fix, or measured FPS improvement. The source script fails if its pinned upstream anchors differ.

## Build status
Repository renamed for compatibility with Windows GitHub Actions runners. Initial native-build validation is underway; APK availability depends on the workflow succeeding.
