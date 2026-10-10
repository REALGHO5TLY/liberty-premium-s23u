#!/usr/bin/env python3
"""Pinned upstream patch: swipe camera, touch settings, reversible audio buffering."""
from pathlib import Path
import argparse

MARK = "PREMIUM_TOUCH_PATCH_V1"
def one(src, before, after):
    n=src.count(before)
    if n != 1:
        raise RuntimeError(f"Expected one matching upstream anchor, found {n}: {before[:100]!r}")
    return src.replace(before,after,1)

def prefs(h,c):
    h=one(h,"  bool haptics = true;\n", """  bool haptics = true;
  // PREMIUM_TOUCH_PATCH_V1: saved swipe sensitivity.
  float gamepad_swipe_x = 1.0f;
  float gamepad_swipe_y = 1.0f;
""")
    c=one(c,"  p.flight_sensitivity = Bounded(p.flight_sensitivity, 0.1f, 3.0f, 1.0f);\n",
"""  p.flight_sensitivity = Bounded(p.flight_sensitivity, 0.1f, 3.0f, 1.0f);
  p.gamepad_swipe_x = Bounded(p.gamepad_swipe_x, 0.25f, 4.0f, 1.0f);
  p.gamepad_swipe_y = Bounded(p.gamepad_swipe_y, 0.25f, 4.0f, 1.0f);
""")
    c=one(c,"            p.invert_camera_y >> p.haptics) g_preferences = Sanitize(p);",
"""            p.invert_camera_y >> p.haptics) {
          // Old 10-value preferences remain compatible with the 2 new values.
          if (!(row >> p.gamepad_swipe_x >> p.gamepad_swipe_y))
            p.gamepad_swipe_x = p.gamepad_swipe_y = 1.0f;
          g_preferences = Sanitize(p);
        }""")
    c=one(c,"         << p.floating_stick << ' ' << p.invert_camera_y << ' ' << p.haptics << '\\n';",
"""         << p.floating_stick << ' ' << p.invert_camera_y << ' ' << p.haptics << ' '
         << p.gamepad_swipe_x << ' ' << p.gamepad_swipe_y << '\\n';""")
    return h,c

def overlay(c):
    c=one(c,'#include "input/gamepad_touch_overlay.h"',
          '#include "input/gamepad_touch_overlay.h"\n#include "input/context_touch_settings.h" // PREMIUM_TOUCH_PATCH_V1')
    c=one(c,'#include <cmath>\n','#include <cmath>\n#include <cstdio>\n')
    c=one(c,'enum class Kind : uint8_t { kStick, kButton, kTrigger, kArrow };',
          'enum class Kind : uint8_t { kStick, kButton, kTrigger, kArrow, kSettings, kSlider, kInvert };')
    # Original layout has 18 active controls, and the panel adds 6.
    c=one(c,'constexpr size_t kControlCount = 20;','constexpr size_t kControlCount = 24;')
    c=one(c,'struct Finger {\n  int control = -1;\n};',
          'struct Finger {\n  int control = -1;\n  ImVec2 previous{0, 0};\n};')
    c=one(c,'  bool visible = false;\n  std::array<Control, kControlCount> controls{};',
"""  bool visible = false;
  bool settings_open = false;
  float swipe_pending_x = 0.0f, swipe_pending_y = 0.0f;
  std::array<Control, kControlCount> controls{};""")
    c=one(c,'std::array<Control, kControlCount> BuildLayout(float w, float h) {',
          'std::array<Control, kControlCount> BuildLayout(float w, float h, bool settings_open) {')
    c=one(c,'    c[n++] = Control{kind, x, y, r, button, index, label, color};',
"""    const float scale = (kind == Kind::kStick || kind == Kind::kButton ||
                         kind == Kind::kArrow || kind == Kind::kTrigger)
                            ? gta4::input::GetContextTouchPreferences().button_scale : 1.0f;
    c[n++] = Control{kind, x, y, r * scale, button, index, label, color};""")
    c=one(c,'  return c;\n}\n\n// The button under a finger, or the stick',
"""  add(Kind::kSettings, w - 0.085f * h, 0.085f * h, 0.046f * h, 0, 0, "LOOK");
  if (settings_open) {
    add(Kind::kSlider, 0.73f * w, 0.26f * h, 0.045f * h, 0, 0, "Horizontal");
    add(Kind::kSlider, 0.73f * w, 0.37f * h, 0.045f * h, 0, 1, "Vertical");
    add(Kind::kSlider, 0.73f * w, 0.48f * h, 0.045f * h, 0, 2, "Control size");
    add(Kind::kSlider, 0.73f * w, 0.59f * h, 0.045f * h, 0, 3, "Opacity");
    add(Kind::kInvert, 0.73f * w, 0.70f * h, 0.050f * h, 0, 0, "INV Y");
  }
  return c;
}

// The button under a finger, or the stick""")
    c=one(c,'int HitTest(const std::array<Control, kControlCount>& controls, float px, float py, float w) {',
          'int HitTest(const std::array<Control, kControlCount>& controls, float px, float py, float w, bool settings_open) {')
    c=one(c,"    if (control.r <= 0.0f || control.kind == Kind::kStick) continue;\n    const float capture = control.r * 1.25f;",
"""    if (control.r <= 0.0f || control.kind == Kind::kStick) continue;
    if (settings_open && control.kind != Kind::kSettings &&
        control.kind != Kind::kSlider && control.kind != Kind::kInvert) continue;
    if (control.kind == Kind::kSlider) {
      if (std::abs(px - control.x) <= w * 0.17f &&
          std::abs(py - control.y) <= control.r * 1.6f) return int(i);
      continue;
    }
    const float capture = control.r * 1.25f;""")
    c=one(c,'  return int(px < w * 0.5f ? kLeftStick : kRightStick);',
          '  if (settings_open) return -1;\n  return int(px < w * 0.5f ? kLeftStick : kRightStick);')
    c=one(c,'    if (control.r <= 0.0f) continue;\n    const bool active = s.held[i];',
          '    if (control.r <= 0.0f || control.kind == Kind::kSlider) continue;\n    const bool active = s.held[i];')
    c=one(c,'      if (control.index == 1 && !active) continue;',
          '      if (control.index == 1) continue;  // right side is swipe-to-look')
    # Draw the settings panel in the game's overlay, without stealing SDL events.
    c=one(c,'\n}\n\n}  // namespace\n\nbool GamepadTouchLayoutSelected() noexcept {',
"""
  if (s.settings_open) {
    const float w = ImGui::GetIO().DisplaySize.x;
    const float h = ImGui::GetIO().DisplaySize.y;
    const ImVec2 a(0.54f * w, 0.12f * h), b(0.93f * w, 0.80f * h);
    draw->AddRectFilled(a,b,IM_COL32(12,20,30,231),h*0.025f);
    draw->AddRect(a,b,IM_COL32(110,185,235,170),h*0.025f);
    draw->AddText(font,font_size,ImVec2(a.x+h*0.03f,a.y+h*0.018f),
                  IM_COL32(235,245,255,245),"SWIPE CAMERA | SETTINGS");
    const auto prefs = gta4::input::GetContextTouchPreferences();
    for (const auto& ctrl : s.controls) {
      if (ctrl.kind != Kind::kSlider) continue;
      const float value = ctrl.index == 0 ? prefs.gamepad_swipe_x :
                          ctrl.index == 1 ? prefs.gamepad_swipe_y :
                          ctrl.index == 2 ? prefs.button_scale : prefs.opacity;
      const float half=0.145f*w, start=ctrl.x-half;
      const float low=ctrl.index<2?0.25f:ctrl.index==2?0.65f:0.20f;
      const float high=ctrl.index<2?4.0f:ctrl.index==2?1.45f:1.00f;
      const float position = start + 2.0f*half*((value-low)/(high-low));
      draw->AddLine(ImVec2(start,ctrl.y),ImVec2(start+2.0f*half,ctrl.y),
                    IM_COL32(100,120,150,220),h*0.012f);
      draw->AddLine(ImVec2(start,ctrl.y),ImVec2(position,ctrl.y),
                    IM_COL32(65,205,235,255),h*0.012f);
      draw->AddCircleFilled(ImVec2(position,ctrl.y),h*0.024f,IM_COL32(240,248,255,255));
      char label[100];
      std::snprintf(label,sizeof(label),"%s: %.2f",ctrl.label,value);
      draw->AddText(font,font_size,ImVec2(start,ctrl.y-h*0.07f),
                    IM_COL32(220,235,245,245),label);
    }
    draw->AddText(font,font_size,ImVec2(0.59f*w,0.74f*h),
                  IM_COL32(218,240,255,230),
                  prefs.invert_camera_y?"Invert Y: ON":"Invert Y: OFF");
  }
}

}  // namespace

bool GamepadTouchLayoutSelected() noexcept {""")
    c=one(c,'    s.fingers.clear();\n    s.held.fill(false);',
          '    s.fingers.clear();\n    s.swipe_pending_x = s.swipe_pending_y = 0.0f;\n    s.held.fill(false);')
    c=one(c,'  s.controls = BuildLayout(width, height);',
          '  s.controls = BuildLayout(width, height, s.settings_open);')
    c=one(c,'      int control = HitTest(s.controls, position.x, position.y, width);',
          '      int control = HitTest(s.controls, position.x, position.y, width, s.settings_open);')
    c=one(c,'      found = s.fingers.emplace(key, Finger{control}).first;',
"""      if (control >= 0 && s.controls[control].kind == Kind::kSettings) {
        s.settings_open = !s.settings_open;
        if (!s.settings_open) gta4::input::FlushContextTouchSettings();
        s.swipe_pending_x = s.swipe_pending_y = 0.0f;
        control = -1;
      } else if (control >= 0 && s.controls[control].kind == Kind::kInvert) {
        auto p = gta4::input::GetContextTouchPreferences();
        p.invert_camera_y = !p.invert_camera_y;
        gta4::input::SetContextTouchPreferences(p);
        control = -1;
      }
      found = s.fingers.emplace(key, Finger{control, position}).first;""")
    c=one(c,'    s.held[control_index] = true;\n    if (control.kind != Kind::kStick) continue;',
"""    s.held[control_index] = true;
    if (control.kind == Kind::kSlider) {
      const float f = std::clamp((position.x - (control.x-width*0.145f)) /
                                  (width*0.29f),0.0f,1.0f);
      auto p = gta4::input::GetContextTouchPreferences();
      const float low=control.index<2?0.25f:control.index==2?0.65f:0.20f;
      const float high=control.index<2?4.0f:control.index==2?1.45f:1.0f;
      const float v=low+f*(high-low);
      if (control.index==0) p.gamepad_swipe_x=v;
      else if (control.index==1) p.gamepad_swipe_y=v;
      else if (control.index==2) p.button_scale=v;
      else p.opacity=v;
      gta4::input::SetContextTouchPreferences(p);
      continue;
    }
    if (control.kind != Kind::kStick) continue;
    if (control.index == 1) {
      const auto p = gta4::input::GetContextTouchPreferences();
      const float denom = std::max(1.0f,height*0.035f);
      const float dx=(position.x-found->second.previous.x)/denom;
      const float dy=(position.y-found->second.previous.y)/denom;
      s.swipe_pending_x=std::clamp(s.swipe_pending_x+dx*p.gamepad_swipe_x,-1.0f,1.0f);
      s.swipe_pending_y=std::clamp(s.swipe_pending_y+dy*p.gamepad_swipe_y*
                                   (p.invert_camera_y?-1.0f:1.0f),-1.0f,1.0f);
      found->second.previous=position;
      stick_owned[1]=true;
      continue;
    }""")
    c=one(c,'  for (int i = 0; i < 2; ++i) {\n    if (!stick_owned[i]) s.stick_x[i] = s.stick_y[i] = 0.0f;\n  }',
"""  for (int i=0;i<2;++i) {
    if (!stick_owned[i]) s.stick_x[i]=s.stick_y[i]=0.0f;
  }
  if (!stick_owned[1] || s.settings_open)
    s.swipe_pending_x=s.swipe_pending_y=0.0f;""")
    c=one(c,'  stick(0, &lx, &ly);\n  stick(1, &rx, &ry);',
"""  stick(0,&lx,&ly);
  const auto to_axis = [](float v)->int16_t {
    return std::abs(v)<0.006f ? 0 : int16_t(std::clamp(v,-1.0f,1.0f)*32767.0f);
  };
  rx=to_axis(s.swipe_pending_x);
  ry=to_axis(-s.swipe_pending_y);
  s.swipe_pending_x=s.swipe_pending_y=0.0f;""")
    c=one(c,'    } else if (control.kind != Kind::kStick) {\n      buttons |= control.button;\n    }',
"""    } else if (control.kind == Kind::kButton || control.kind == Kind::kArrow) {
      buttons |= control.button;
    }""")
    return c

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    r=args.root.resolve()
    files={
      "overlay":r/"glue/rexglue-sdk-main/gta4-recomp/src/input/gamepad_touch_overlay.cpp",
      "h":r/"glue/rexglue-sdk-main/gta4-recomp/src/input/context_touch_settings.h",
      "cpp":r/"glue/rexglue-sdk-main/gta4-recomp/src/input/context_touch_settings.cpp",
      "defaults":r/"os/android/app/src/main/assets/default_args.txt",
      "gradle":r/"os/android/app/build.gradle.kts"
    }
    src={k:p.read_text(encoding="utf-8") for k,p in files.items()}
    if MARK in src["overlay"]:
        print("Patch already applied")
        return
    h,cpp=prefs(src["h"],src["cpp"])
    defaults=src["defaults"]
    if "--audio_maxqframes=" in defaults:
        raise RuntimeError("Upstream changed audio defaults; inspect first.")
    defaults += """
# Reversible audio queue experiment; retains original world/graphics.
--audio_maxqframes=48
--android_pin_hot_threads=false
"""
    gradle=one(src["gradle"],'applicationId = "com.libertyrecomp"',
               'applicationId = "com.libertyrecomp.premium"')
    gradle=one(gradle,'versionName   = "0.5.8.1"',
               'versionName   = "0.5.8.1-premium1"')
    updated={"overlay":overlay(src["overlay"]),"h":h,"cpp":cpp,
             "defaults":defaults,"gradle":gradle}
    for k,p in files.items():
        if updated[k]==src[k]: raise RuntimeError(f"No change to {p}")
        print("Validated",p.relative_to(r))
        if not args.check_only: p.write_text(updated[k],encoding="utf-8")
    print("Premium patch applied." if not args.check_only else "All patch anchors valid.")

if __name__=="__main__":
    main()
