# Liberty Premium S23U — GTA IV Android

An experimental Android arm64 patch on pinned [LibertyRecompAndroid 0.5.8.1](https://github.com/vaduur/LibertyRecompAndroid), built by GitHub Actions. **Not affiliated with Rockstar; no GTA IV game assets are included.**

## V2: Smoothness and audio experiment

- **No visual or population downgrade:** 720p native, FXAA, original shadows and reflections, draw distance fixed at 1.0; traffic, parked vehicles and pedestrians remain at their prior values. The performance patch explicitly does *not* alter those values.
- **Touch overlay:** keep swipe-to-look and X/Y sensitivity plus invert Y, button scale and opacity. Read preferences once when constructing the layout rather than locking separately for every button.
- **Audio callback:** shorten the time the callback holds the queue mutex. Sample conversion and SDL audio stream submission now occur outside the queue lock, avoiding contention with the audio producer. Count empty callbacks in logs periodically.
- **Audio delay:** use 40 blocks (~213 ms) instead of the prior experiment's 48 blocks (~256 ms). Clearer audio is not guaranteed; hardware listening tests still required.
- **Frame pacing:** choose `smooth` (40 FPS limiter, best evaluated with phone set to 120 Hz) or `high` (60 FPS limiter; targets a higher peak but can stutter if the scene cannot sustain it). Both have unchanged graphics and pedestrians.
- **Separate package:** `com.libertyrecomp.premium.v2` protects the original XHYN installation *and* premium v1. Requires its own game-data installation. Android debug signing may differ between GitHub runs.

The original fork's performance improvements (v0.5.8/0.5.8.1) are already in the pinned source. It is **not possible to promise 50/60 FPS or completely stutter-free gameplay without measuring frame times on the S23 Ultra**. More engine work will be required if native renderer/game processing is the limit.

## Building an APK

Go to [GitHub Actions](https://github.com/REALGHO5TLY/liberty-premium-s23u/actions/workflows/build-premium-android.yml). Choose **Run workflow** and **smooth** for the initial test, or **high** to test the 60 FPS ceiling. A push to main automatically builds smooth. Once green, download `Liberty-Premium-S23U-v2-smooth-APK` or `Liberty-Premium-S23U-v2-high-APK` from the build's **Artifacts** section, then extract and install the APK. It does not overwrite XHYN.

The new app creates `Android/data/com.libertyrecomp.premium.v2/files/args.txt` **on first start**. If that file already exists, switching the APK from smooth to high or vice versa DOES NOT change its existing frame cap. Update `--gta4_frame_limit=40` to `--gta4_frame_limit=60` (or the reverse) in that `args.txt` and completely restart the app to switch modes without reinstalling.

## Proper A/B testing to isolate stutters

1. Use the same game scene, weather, traffic conditions, driver and full resolution on both XHYN and Premium V2. Keep all quality sliders identical.
2. Make one complete drive to populate shader caches before benchmarking. Time multiple full runs of the same route, with the phone at similar temperature.
3. Set Samsung **Motion smoothness: Adaptive (120 Hz)** and disable battery saver. Prefer Samsung Game Booster's Performance setting if available. Do not use a screenshot or frame-cap change as proof of better rendering performance.
4. For diagnosis (not everyday play) use the port's **Play (Debug Log)** to collect `last_launch.txt` and `debug_logs/debug-*.log`, especially if audio crackles. This contains driver and audio data.
5. At a constant 40 FPS expect 25 ms/frame. At 50 FPS expect 20 ms/frame. Report the actual FPS and any large spikes; a 60 FPS cap is a ceiling, not a guarantee of 60.
6. If the game cannot sustain 40 at identical quality, a 30 FPS lock may feel smoother without reducing rendering quality, but that is a fallback and not our optimisation goal.

### Important limitations

The known stutter causes may include shader compilation, streaming, renderer CPU frame-recording cost, thermal throttling or audio producer underruns. Reducing mutex contention addresses a specific possible cause, not all of them. The perf-focused code is intentionally conservative: experimental settings which disable shadows/reflections or reduce traffic or draw distance have **not** been enabled.

Source: `premium_patch/apply.py` (v1 controls) + `premium_patch/performance_v2.py` (new audio/performance patch) against commit `4f6ce516eb1cf606dadacaa63c5f63f00f751a55`.
