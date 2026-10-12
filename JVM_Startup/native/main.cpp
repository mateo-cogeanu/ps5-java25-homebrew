/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "demo_renderer.hpp"
#include "pad.h"
#include <cstdint>
#include <cstdio>
extern "C" std::uint64_t sceKernelGetProcessTime();
namespace {
using ps5::demo::Canvas;
constexpr std::uint32_t rgb(unsigned r, unsigned g, unsigned b) {
  return 0xff000000u | r | (g << 8) | (b << 16);
}
constexpr auto white = rgb(238, 242, 250), muted = rgb(139, 153, 178),
               accent = rgb(109, 156, 255);
constexpr auto panel = rgb(25, 34, 51), border = rgb(48, 64, 90),
               base = rgb(12, 19, 32);
PadSample state{};
int handle = -1, error_code = 0, page = 0, focus = 0, direction = 0;
std::uint64_t last_sample = 0, last_move = 0;
std::uint32_t previous = 0;
bool sidebar = false, detail = false, connected = false;
const char *pages[] = {"Explore", "Collections", "Appearance"};
const char *titles[][3] = {
    {"A fresh start", "Room for ideas", "The playground"},
    {"Your favourites", "Recently visited", "Something new"},
    {"Midnight", "Soft contrast", "A touch of blue"}};
const char *subtitles[][3] = {
    {"Space to begin.", "Keep a little curiosity.", "Follow your controller."},
    {"A place for what you love.", "Pick up where you left off.",
     "Leave space to discover."},
    {"Calm, deep, and focused.", "A softer kind of clarity.",
     "Just enough colour."}};
void neutral() {
  state = {};
  state.lx = state.ly = state.rx = state.ry = 128;
}
void move(int dir) {
  if (detail)
    return;
  if (sidebar) {
    if (dir == 1)
      page = (page + 2) % 3;
    if (dir == 2)
      page = (page + 1) % 3;
    if (dir == 4) {
      sidebar = false;
      focus = 0;
    }
  } else {
    if (dir == 3) {
      if (focus == 0)
        sidebar = true;
      else
        --focus;
    }
    if (dir == 4 && focus < 2)
      ++focus;
  }
}
void input() {
  if (handle < 0)
    return;
  PadSample batch[64]{};
  // Drain retained records before rendering, including press/release edges.
  for (int read = 0; read < 8; ++read) {
    int count = scePadRead(handle, batch, 64);
    if (count < 0 || count > 64) {
      error_code = count;
      connected = false;
      neutral();
      previous = 0;
      direction = 0;
      return;
    }
    for (int i = 0; i < count; ++i) {
      last_sample = sceKernelGetProcessTime();
      connected = batch[i].connected && !(batch[i].buttons & 0x80000000u);
      if (connected)
        state = batch[i];
      else
        neutral();
      error_code = 0;
      auto pressed = state.buttons & ~previous;
      previous = state.buttons;
      if (pressed & 0x4000u) {
        if (detail)
          detail = false;
        else if (sidebar)
          sidebar = false;
        else
          detail = true;
      }
      if (pressed & 0x2000u) {
        if (detail)
          detail = false;
        else
          sidebar = !sidebar;
      }
      int dir = pressed & 0x10   ? 1
                : pressed & 0x40 ? 2
                : pressed & 0x80 ? 3
                : pressed & 0x20 ? 4
                                 : 0;
      if (dir) {
        move(dir);
        last_move = last_sample;
        direction = dir;
      }
    }
    if (count < 64)
      break;
  }
  auto now = sceKernelGetProcessTime();
  if (now - last_sample > 1000000) {
    connected = false;
    neutral();
    previous = 0;
    direction = 0;
  }
  int dir = state.buttons & 0x10   ? 1
            : state.buttons & 0x40 ? 2
            : state.buttons & 0x80 ? 3
            : state.buttons & 0x20 ? 4
            : state.lx < 70        ? 3
            : state.lx > 186       ? 4
            : state.ly < 70        ? 1
            : state.ly > 186       ? 2
                                   : 0;
  if (!dir)
    direction = 0;
  else if (dir != direction || now - last_move >= 260000) {
    move(dir);
    direction = dir;
    last_move = now;
  }
}
void icon(Canvas &c, int x, int y, int kind, std::uint32_t color) {
  if (kind == 0) {
    c.rounded(x, y, 28, 28, 8, color);
    c.rounded(x + 38, y, 28, 28, 8, color);
    c.rounded(x, y + 38, 28, 28, 8, color);
    c.rounded(x + 38, y + 38, 28, 28, 8, color);
  } else if (kind == 1) {
    c.rounded(x, y + 17, 66, 49, 10, color);
    c.rounded(x + 6, y + 5, 52, 8, 4, color);
    c.rounded(x + 13, y - 6, 38, 7, 3, color);
  } else {
    c.disc(x + 33, y + 33, 31, color);
    c.disc(x + 33, y + 33, 19, panel);
    c.disc(x + 33, y + 33, 8, color);
  }
}
void hint(Canvas &c, int x, int y, const char *symbol, const char *text) {
  c.rounded(x, y, 34, 34, 17, border);
  c.label(x + 10, y + 3, symbol, 20, white);
  c.label(x + 49, y + 3, text, 20, muted);
}
void scene(Canvas &c) noexcept {
  c.gradient(rgb(18, 29, 49), rgb(8, 13, 23));
  c.rounded(48, 48, 308, 984, 32, rgb(17, 25, 40));
  c.rounded(85, 92, 48, 48, 15, accent);
  c.label(99, 93, "S", 30, base);
  c.label(151, 94, "Studio", 30, white);
  c.label(86, 173, "A space to explore", 20, muted);
  for (int i = 0; i < 3; ++i) {
    int y = 300 + i * 92;
    if (page == i) {
      if (sidebar)
        c.rounded(76, y - 2, 254, 70, 18, accent);
      c.rounded(80, y + 2, 246, 62, 15, rgb(35, 49, 72));
      c.rounded(91, y + 19, 4, 29, 2, accent);
    }
    c.label(114, y + 13, pages[i], 24, page == i ? white : muted);
  }
  c.disc(95, 913, 5, connected ? rgb(105, 215, 172) : rgb(230, 176, 91));
  c.label(113, 899,
          connected ? "Controller connected" : "Controller unavailable", 20,
          muted);
  c.label(86, 955, "Interface study 02", 20, rgb(91, 107, 135));
  c.label(420, 84, pages[page], 24, muted);
  c.label(420, 130,
          page == 0   ? "Make yourself at home."
          : page == 1 ? "A place for your favourites."
                      : "Find your atmosphere.",
          64, white);
  c.label(422, 228,
          page == 0   ? "Take your time. There is room to try things."
          : page == 1 ? "A few spaces, ready for whatever comes next."
                      : "A small study in colour, clarity, and focus.",
          24, muted);
  c.rounded(1706, 79, 130, 40, 20, rgb(32, 45, 65));
  c.label(1730, 86, "Preview", 20, muted);
  c.rounded(420, 316, 1416, 294, 28, rgb(27, 43, 68));
  c.rounded(454, 350, 172, 36, 18, rgb(48, 70, 105));
  c.label(474, 355, "Just exploring", 20, rgb(188, 211, 253));
  c.label(456, 411,
          page == 0   ? "Small steps. New possibilities."
          : page == 1 ? "Good things take a little space."
                      : "Less noise. More breathing room.",
          42, white);
  c.label(457, 490, "Move through the cards and see what feels right.", 24,
          rgb(171, 189, 216));
  c.label(457, 533, "This is a visual playground. Nothing to configure yet.",
          20, muted);
  c.disc(1648, 456, 104, rgb(46, 68, 106));
  c.disc(1648, 456, 76, rgb(69, 102, 158));
  c.disc(1648, 456, 43, rgb(136, 176, 245));
  c.disc(1674, 432, 15, rgb(205, 224, 255));
  c.label(422, 650, page == 2 ? "Palette previews" : "Choose a space", 30,
          white);
  char position[16];
  std::snprintf(position, sizeof(position), "%02d / 03", focus + 1);
  c.label(1642, 661, position, 20, muted);
  for (int i = 0; i < 3; ++i) {
    int x = 420 + i * 484;
    bool selected = !sidebar && focus == i;
    if (selected)
      c.rounded(x - 4, 716, 456, 220, 26, accent);
    c.rounded(x, 720, 448, 212, 23, selected ? rgb(32, 47, 72) : panel);
    icon(c, x + 31, 747, i, selected ? rgb(170, 202, 255) : rgb(108, 132, 168));
    c.label(x + 30, 828, titles[page][i], 30, white);
    c.label(x + 30, 878, subtitles[page][i], 20, muted);
    if (selected)
      c.disc(x + 406, 754, 5, accent);
  }
  hint(c, 425, 976, "X", "Explore");
  hint(c, 618, 976, "O", "Back");
  c.label(780, 982, "D-pad / left stick to move", 20, muted);
  c.label(1555, 982, "PS button to close", 20, muted);
  if (error_code) {
    char msg[64];
    std::snprintf(msg, sizeof(msg), "Controller error %08X",
                  static_cast<unsigned>(error_code));
    c.label(420, 278, msg, 20, rgb(230, 176, 91));
  }
  if (detail) {
    c.tint(rgb(4, 8, 16), 150);
    c.rounded(690, 354, 650, 378, 32, rgb(8, 14, 24));
    c.rounded(686, 345, 650, 378, 32, border);
    c.rounded(688, 347, 646, 374, 30, rgb(23, 34, 52));
    c.label(730, 392, titles[page][focus], 42, white);
    c.label(733, 473, "Just a little preview for now.", 24, muted);
    c.label(733, 517, "More possibilities can come later.", 24, muted);
    c.rounded(731, 602, 556, 65, 18, accent);
    c.label(891, 616, "X  Keep exploring", 24, base);
  }
}
struct VisibleState {
  int page, focus, error;
  bool sidebar, detail, connected;
  bool operator==(const VisibleState &) const = default;
};
VisibleState visible_state() {
  return {page, focus, error_code, sidebar, detail, connected};
}
bool update() noexcept {
  auto before = visible_state();
  input();
  return !(before == visible_state());
}
} // namespace
int main() {
  neutral();
  (void)sceUserServiceInitialize(nullptr);
  std::int32_t user = -1;
  error_code = sceUserServiceGetInitialUser(&user);
  if (error_code >= 0) {
    error_code = scePadInit();
    if (error_code >= 0) {
      handle = scePadOpen(user, 0, 0, nullptr);
      error_code = handle < 0 ? handle : 0;
    }
  }
  ps5::demo::run_ui(scene, update, "Interface Lab ready");
}
