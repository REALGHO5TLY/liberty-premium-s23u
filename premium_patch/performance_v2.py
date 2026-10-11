#!/usr/bin/env python3
"""Premium v2, quality-preserving runtime experiment on top of apply.py.

No graphic-resolution, draw-count, pedestrian or traffic changes. The script
refuses to modify source that does not match the audited upstream anchors.
"""
from pathlib import Path
import argparse

def replace_one(src, needle, replacement, label):
    count = src.count(needle)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, got {count}: {needle[:120]!r}")
    return src.replace(needle, replacement, 1)

def patch_overlay(src):
    # The v1 overlay acquired the preferences mutex once PER BUTTON while
    # assembling 18 controls each frame. Read once per layout instead.
    src = replace_one(
        src,
        '  size_t n = 0;\n  const auto add = [&](Kind kind, float x, float y, float r, uint16_t button, uint8_t index,',
        '  size_t n = 0;\n  const auto prefs = gta4::input::GetContextTouchPreferences();\n  const auto add = [&](Kind kind, float x, float y, float r, uint16_t button, uint8_t index,',
        "touch-settings snapshot")
    src = replace_one(
        src,
        '? gta4::input::GetContextTouchPreferences().button_scale : 1.0f;',
        '? prefs.button_scale : 1.0f;',
        "button-scale mutex elimination")
    # Opacity slider was stored but its value never affected the default
    # gamepad overlay. Apply it while preserving the user's control layout.
    src = replace_one(
        src,
        'void Draw(ImDrawList* draw, ImFont* font, float font_size, const State& s) {\n',
        'void Draw(ImDrawList* draw, ImFont* font, float font_size, const State& s) {\n'
        '  const auto opacity = gta4::input::GetContextTouchPreferences().opacity;\n'
        '  const auto alpha = [&](int base) -> int {\n'
        '    return std::clamp(int(float(base) * (opacity / 0.65f)), 0, 255);\n'
        '  };\n',
        "opacity control")
    src = replace_one(
        src,
        '      draw->AddCircleFilled(center, radius, kFill, 48);',
        '      draw->AddCircleFilled(center, radius, IM_COL32(90,90,90,alpha(55)), 48);',
        "left stick opacity")
    src = replace_one(
        src,
        '    draw->AddCircleFilled(center, radius, active ? kFillHeld : kFill, 48);',
        '    draw->AddCircleFilled(center, radius,\n'
        '                          active ? IM_COL32(200,200,200,alpha(105))\n'
        '                                 : IM_COL32(90,90,90,alpha(55)), 48);',
        "button opacity")
    # Prevent snapping the swiped camera to zero while the finger is still
    # down and gameplay/rendering input reads run at differing frequencies.
    # v1 already provides per-frame deltas; keep the same swipe behaviour.
    return src

def patch_audio(src):
    # In upstream, the SDL realtime callback kept frames_mutex_ locked not
    # just for popping a buffer, but also for conversion and SDL submission.
    # This blocked SubmitFrame on the audio worker and could cause underruns.
    # Lock only the short queue/pop and recycle operations.
    src = replace_one(
        src,
        '#include <array>\n#include <chrono>',
        '#include <array>\n#include <atomic>\n#include <chrono>',
        "audio atomic include")
    src = replace_one(
        src,
        '    std::unique_lock<std::mutex> guard(driver->frames_mutex_);\n'
        '    if (driver->frames_queued_.empty()) {',
        '    float* buffer = nullptr;\n'
        '    {\n'
        '      std::lock_guard<std::mutex> queue_lock(driver->frames_mutex_);\n'
        '      if (!driver->frames_queued_.empty()) {\n'
        '        buffer = driver->frames_queued_.front();\n'
        '        driver->frames_queued_.pop();\n'
        '      }\n'
        '    }\n'
        '    if (!buffer) {',
        "short audio queue lock")
    src = replace_one(
        src,
        '      auto buffer = driver->frames_queued_.front();\n'
        '      driver->frames_queued_.pop();\n'
        '      if (REXCVAR_GET(audio_mute)) {',
        '      if (REXCVAR_GET(audio_mute)) {',
        "remove duplicated audio pop")
    src = replace_one(
        src,
        '      if (!SDL_PutAudioStreamData(stream, data, len)) {\n'
        '        REXAPU_ERROR("SDL_PutAudioStreamData() failed: {}", SDL_GetError());\n'
        '        driver->frames_unused_.push(buffer);\n'
        '        break;\n'
        '      }\n'
        '      driver->frames_unused_.push(buffer);\n'
        '\n'
        '      auto ret = driver->semaphore_->Release(1, nullptr);',
        '      const bool submitted = SDL_PutAudioStreamData(stream, data, len);\n'
        '      {\n'
        '        std::lock_guard<std::mutex> recycle_lock(driver->frames_mutex_);\n'
        '        driver->frames_unused_.push(buffer);\n'
        '      }\n'
        '      if (!submitted) {\n'
        '        REXAPU_ERROR("SDL_PutAudioStreamData() failed: {}", SDL_GetError());\n'
        '        break;\n'
        '      }\n'
        '\n'
        '      auto ret = driver->semaphore_->Release(1, nullptr);',
        "audio unlocked conversion / submission")
    src = replace_one(
        src,
        '    if (!buffer) {\n'
        '      if (sdl_callback_count < 10) {',
        '    if (!buffer) {\n'
        '      // Log intermittently only during underruns; keep the real-time\n'
        '      // callback quiet on its normal, successful path.\n'
        '      static std::atomic<uint32_t> empty_callbacks{0};\n'
        '      const auto empty_count = empty_callbacks.fetch_add(1, std::memory_order_relaxed) + 1;\n'
        '      if (empty_count == 1 || empty_count % 4096 == 0)\n'
        '        REXAPU_WARN("Audio output buffer empty, occurrence {}", empty_count);\n'
        '      if (sdl_callback_count < 10) {',
        "audio underrun counters")
    return src

def patch_defaults(src, limit):
    src = replace_one(src, '--audio_maxqframes=48', '--audio_maxqframes=40',
                      "moderate audio queue depth")
    src = replace_one(src, '--gta4_frame_limit=30',
                      f'--gta4_frame_limit={limit}', "frame-cap control")
    # Stable world detail: dynamic scaling changes draw distance dynamically,
    # and can vary scene geometry/fps. Keep the original 1.0 render distance.
    # Never touch resolution, upscaler, anti-aliasing, effects or populations.
    src = replace_one(src,'--gta4_dynamic_draw_distance=true',
                      '--gta4_dynamic_draw_distance=false',
                      "fixed console draw distance")
    return src

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=['smooth','high'],default='smooth')
    p.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    root=args.root.resolve()
    paths={
       'touch':root/'glue/rexglue-sdk-main/gta4-recomp/src/input/gamepad_touch_overlay.cpp',
       'audio':root/'glue/rexglue-sdk-main/src/audio/sdl/sdl_audio_driver.cpp',
       'defaults':root/'os/android/app/src/main/assets/default_args.txt',
       'gradle':root/'os/android/app/build.gradle.kts',
    }
    before={k:pp.read_text(encoding='utf-8') for k,pp in paths.items()}
    for key in ('touch','defaults'):
        if 'PREMIUM_TOUCH_PATCH_V1' not in before['touch']:
            raise RuntimeError("Apply premium_patch/apply.py BEFORE performance_v2.py")
    updated={}
    updated['touch']=patch_overlay(before['touch'])
    updated['audio']=patch_audio(before['audio'])
    updated['defaults']=patch_defaults(before['defaults'],40 if args.mode=='smooth' else 60)
    updated['gradle']=replace_one(before['gradle'],
            'applicationId = "com.libertyrecomp.premium"',
            'applicationId = "com.libertyrecomp.premium.v2"',
            'separate v2 package identity')
    updated['gradle']=replace_one(updated['gradle'],
            'versionName   = "0.5.8.1-premium1"',
            'versionName   = "0.5.8.1-premium2"',
            'v2 version name')
    for key,pp in paths.items():
        if updated[key]==before[key]:raise RuntimeError("No change to "+str(pp))
        print('OK '+str(pp.relative_to(root)))
    if not args.check_only:
        for key,pp in paths.items():
            pp.write_text(updated[key],encoding='utf-8')
    print(f"Quality-preserving v2 mode={args.mode}, frame limit={40 if args.mode=='smooth' else 60} "
          + ("validated" if args.check_only else "applied"))

if __name__=='__main__':
    main()
