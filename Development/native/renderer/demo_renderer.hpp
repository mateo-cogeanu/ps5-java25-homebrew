/*
 * ps5-native-app-boilerplate - Small CPU-rendered demonstration API.
 * Copyright (C) 2026 BlackBearReloaded
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Keeps PS5 VideoOut setup and the bitmap font out of the starter main file.
 */

#pragma once

#include <cstdint>
#include <span>
#include <string_view>

namespace ps5::demo
{
enum class Color : std::uint32_t
{
    background = UINT32_C(0xff190d0a),
    panel = UINT32_C(0xff301f17),
    white = UINT32_C(0xffffffff),
    cyan = UINT32_C(0xffffff00),
    magenta = UINT32_C(0xffff00ff),
    yellow = UINT32_C(0xff00ffff),
};

class Canvas;
using StopScene = bool (*)() noexcept;
using DrawScene = void (*)(Canvas &) noexcept;
using UpdateScene = bool (*)() noexcept;
// Draws the scene once and keeps it on screen.
[[noreturn]] void run(DrawScene draw, std::string_view ready_message) noexcept;
// Calls draw for every frame, for a scene that changes. The callback redraws the whole
// frame; drawing on the CPU, a full 1920x1080 frame takes longer than one display refresh.
[[noreturn]] void run_frames(DrawScene draw, std::string_view ready_message) noexcept;
// Poll independently of rendering; redraw only when visible UI state changes.
[[noreturn]] void run_ui(DrawScene draw, UpdateScene update,
                        std::string_view ready_message) noexcept;

// Returning UI session: closes VideoOut before releasing its mapped buffers.
// False means cleanup failed; callers must not start another display owner.
bool run_ui_until(DrawScene draw, UpdateScene update, StopScene stop,
                  std::string_view ready_message) noexcept;

namespace detail
{
bool present_session(DrawScene draw, std::string_view ready_message, bool every_frame, UpdateScene update, StopScene stop) noexcept;
[[noreturn]] void present(DrawScene draw, std::string_view ready_message,
                          bool every_frame, UpdateScene update = nullptr) noexcept;
}

class Canvas final
{
  public:
    void clear(Color color) noexcept;
    void rectangle(unsigned x, unsigned y, unsigned width, unsigned height, Color color) noexcept;
    void circle(unsigned center_x, unsigned center_y, unsigned radius, Color color) noexcept;
    void triangle(unsigned center_x, unsigned top, unsigned half_width, unsigned height,
                  Color color) noexcept;
    void text(unsigned x, unsigned y, std::string_view value, unsigned scale, Color color) noexcept;
    void gradient(std::uint32_t top, std::uint32_t bottom) noexcept;
    void tint(std::uint32_t color, unsigned alpha) noexcept;
    void rounded(int x, int y, unsigned width, unsigned height, unsigned radius,
                 std::uint32_t color) noexcept;
    void disc(int x, int y, unsigned radius, std::uint32_t color) noexcept;
    void label(int x, int y, std::string_view value, unsigned size,
               std::uint32_t color) noexcept;
    // Publish a complete top-row-first RGBA8 frame into the tiled canvas.
    // Invalid/short input leaves the destination unchanged.
    bool blit_rgba(std::span<const std::uint32_t> pixels, unsigned row_pitch = 1920) noexcept;
    static unsigned text_width(std::string_view value, unsigned size) noexcept;

  private:
    explicit Canvas(std::uint32_t *pixels) noexcept : pixels_{pixels}
    {
    }

    std::uint32_t *pixels_;

    friend bool detail::present_session(DrawScene draw, std::string_view ready_message, bool every_frame, UpdateScene update, StopScene stop) noexcept;
    friend void detail::present(DrawScene draw, std::string_view ready_message,
                                bool every_frame, UpdateScene update) noexcept;
};

void read_asset_text(const char *path, std::span<char> destination,
                     std::string_view fallback) noexcept;
} // namespace ps5::demo
