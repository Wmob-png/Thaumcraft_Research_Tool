# main.py

import pygame
import ctypes
import json
from gui import HexBoard
from resources import resource_path, asset_path

CONFIG_FILE = "solver_config.json"
DEFAULT_CONFIG = {
    "window_width": 1100,
    "window_height": 700,
    "ring_count": 3,
    "oi_chaining": False,
    "show_tooltips": True,
    "show_coords": False,
}

BASE_WIDTH = 1100
BASE_HEIGHT = 700

ALLOWED_SCALES = [0.5, 0.625, 0.75, 0.875, 1.0, 1.125, 1.25, 1.5, 1.75, 2.0]


def get_nearest_scale(width, height):
    scale_x = width / BASE_WIDTH
    scale_y = height / BASE_HEIGHT
    target_scale = min(scale_x, scale_y)
    valid_scales = [s for s in ALLOWED_SCALES if s <= target_scale + 0.01]
    if valid_scales:
        return max(valid_scales)
    return ALLOWED_SCALES[0]


def snap_window_size(width, height):
    scale = get_nearest_scale(width, height)
    return int(BASE_WIDTH * scale), int(BASE_HEIGHT * scale)


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return {**DEFAULT_CONFIG, **config}
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


try:
    ctypes.windll.user32.SetProcessDPIAware()
    user32 = ctypes.windll.user32
except Exception:
    user32 = None

pygame.init()
BASE_FONT_SIZE = 24
font = pygame.font.SysFont(None, BASE_FONT_SIZE)
small_font = pygame.font.SysFont(None, 18)

config = load_config()

WINDOW_WIDTH, WINDOW_HEIGHT = snap_window_size(
    config["window_width"],
    config["window_height"]
)

FLAGS = pygame.RESIZABLE
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), FLAGS)
pygame.display.set_caption("Thaumcraft Research Solver (GTNH)")


def force_topmost():
    if not user32:
        return
    try:
        hwnd = pygame.display.get_wm_info()["window"]
        HWND_TOPMOST  = -1
        SWP_NOMOVE    = 0x0002
        SWP_NOSIZE    = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
    except Exception:
        pass


def draw_board_size_menu():
    screen.fill((30, 30, 30))
    title = font.render("Pick a Hex Grid Size", True, (255, 255, 255))
    screen.blit(title, (WINDOW_WIDTH // 2 - 100, 50))

    subtitle = small_font.render(
        "(Press 1, 2, or 3 to quick-select)", True, (150, 150, 150)
    )
    screen.blit(subtitle, (WINDOW_WIDTH // 2 - 100, 80))

    sizes = [
        ("Small (2 rings) - Press 1", 2),
        ("Medium (3 rings) - Press 2", 3),
        ("Large (4 rings) - Press 3", 4),
    ]

    buttons = []
    for i, (label, rings) in enumerate(sizes):
        rect = pygame.Rect(WINDOW_WIDTH // 2 - 150, 120 + i * 60, 300, 40)
        pygame.draw.rect(screen, (180, 180, 180), rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 2)
        txt = font.render(label, True, (0, 0, 0))
        screen.blit(txt, (rect.x + 15, rect.y + 10))
        buttons.append((rect, rings))

    pygame.display.flip()
    return buttons


def load_icon(name):
    """
    """
    try:
        path = asset_path(name)
        icon = pygame.image.load(path).convert_alpha()
        return icon
    except Exception as e:
        print(f"[Icon] Failed to load {name}: {e}")
        return None


def whiten_surface(surface):
    if not surface:
        return None
    try:
        import pygame.surfarray as surfarray
        import numpy as np
        arr   = surfarray.pixels_alpha(surface)
        white = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        white.fill((255, 255, 255))
        w_arr = surfarray.pixels_alpha(white)
        w_arr[:] = arr
        del arr, w_arr
        return white
    except ImportError:
        surf = surface.copy()
        w, h = surf.get_size()
        for x in range(w):
            for y in range(h):
                r, g, b, a = surf.get_at((x, y))
                if a != 0:
                    surf.set_at((x, y), (255, 255, 255, a))
        return surf


# ── Board size picker ────────────────────────────────────────────────────────

ring_count = config.get("ring_count", 3)
waiting = True

while waiting:
    force_topmost()
    buttons = draw_board_size_menu()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                ring_count = 2
                waiting = False
            elif event.key == pygame.K_2:
                ring_count = 3
                waiting = False
            elif event.key == pygame.K_3:
                ring_count = 4
                waiting = False
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            for rect, rings in buttons:
                if rect.collidepoint(x, y):
                    ring_count = rings
                    waiting = False
                    break

# ── Asset loading ────────────────────────────────────────────────────────────

bg_image = None
try:
    bg_path = asset_path("research_bg.png")
    bg_image = pygame.image.load(bg_path).convert()
    bg_image = pygame.transform.scale(bg_image, (BASE_WIDTH, BASE_HEIGHT))
except Exception:
    pass

# IO and size icons
IO_CENTER_IMG = load_icon("Ordinamentum.png") or load_icon("Ordostrum.png")

SIZE_IMG_1 = load_icon("hex1.png")
SIZE_IMG_2 = load_icon("hex2.png") or SIZE_IMG_1

CLEAR_IMG = load_icon("brain.png")
SOLVE_IMG = load_icon("discovery.png")

# ── Board setup ──────────────────────────────────────────────────────────────

BASE_CENTER = (550, 350)
scale = WINDOW_WIDTH / BASE_WIDTH

board = HexBoard(ring_count=ring_count, center=BASE_CENTER)
board.scale_x = scale
board.scale_y = scale
board.oi_chaining   = config.get("oi_chaining", False)
board.show_tooltips = config.get("show_tooltips", True)
board.show_coords   = config.get("show_coords", False)

BASE_BUTTON_W          = 130
BASE_BUTTON_H          = 60
BASE_BUTTON_SPACING    = 10
BASE_BUTTONS_Y         = BASE_HEIGHT - 80
BASE_TOTAL_BUTTON_WIDTH = BASE_BUTTON_W * 4 + BASE_BUTTON_SPACING * 3
BASE_BUTTONS_LEFT_X    = (BASE_WIDTH - BASE_TOTAL_BUTTON_WIDTH) // 2

io_button      = None
size_button    = None
clear_button   = None
solve_button   = None
credits_button = None

size_flash_frames = 0


def recompute_button_rects():
    global io_button, size_button, clear_button, solve_button, credits_button

    button_w      = int(BASE_BUTTON_W * scale)
    button_h      = int(BASE_BUTTON_H * scale)
    buttons_left_x = int(BASE_BUTTONS_LEFT_X * scale)
    buttons_y     = int(BASE_BUTTONS_Y * scale)
    spacing       = int(BASE_BUTTON_SPACING * scale)

    io_button    = pygame.Rect(buttons_left_x, buttons_y, button_w, button_h)
    size_button  = pygame.Rect(buttons_left_x + button_w + spacing, buttons_y, button_w, button_h)
    clear_button = pygame.Rect(buttons_left_x + 2 * (button_w + spacing), buttons_y, button_w, button_h)
    solve_button = pygame.Rect(buttons_left_x + 3 * (button_w + spacing), buttons_y, button_w, button_h)

    credits_x = int(20 * scale)
    credits_y = buttons_y
    credits_button = pygame.Rect(credits_x, credits_y, button_w, button_h)


recompute_button_rects()


def draw_help_overlay(screen):
    shortcuts = [
        "=== Keyboard Shortcuts ===",
        "",
        "S - Solve board",
        "C - Clear solver placements",
        "Shift+C - Clear ALL",
        "O - Toggle IO chaining",
        "1/2/3 - Set board size",
        "",
        "Ctrl+Z - Undo",
        "Ctrl+Y - Redo",
        "",
        "T - Toggle tooltips",
        "H - Show/hide this help",
        "F2 - Show/hide credits",
        "",
        "ESC - Deselect / Quit / Close overlays",
        "",
        "=== Mouse ===",
        "",
        "Left-click sidebar - Select/deselect",
        "Left-click hex - Place aspect",
        "Right-click hex - Clear/void",
        "Right-click empty - Deselect",
    ]

    line_height = 22
    max_width   = max(font.size(line)[0] for line in shortcuts)
    panel_w     = max_width + 40
    panel_h     = len(shortcuts) * line_height + 30

    panel_x = (WINDOW_WIDTH  - panel_w) // 2
    panel_y = (WINDOW_HEIGHT - panel_h) // 2

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((40, 40, 40, 240))
    pygame.draw.rect(panel, (100, 100, 100), (0, 0, panel_w, panel_h), 2)
    screen.blit(panel, (panel_x, panel_y))

    for i, line in enumerate(shortcuts):
        color = (255, 215, 0) if "===" in line else (255, 255, 255)
        text  = font.render(line, True, color)
        screen.blit(text, (panel_x + 20, panel_y + 15 + i * line_height))


def draw_centered_icon(rect, base_img, active=True, scale_mult=1.0):
    if not base_img:
        return
    min_dim = min(rect.width, rect.height)
    if min_dim <= 0:
        return
    size = min(int(min_dim * 0.9 * scale_mult), min_dim)
    cx, cy = rect.center
    icon_scaled = pygame.transform.smoothscale(base_img, (size, size))
    if not active:
        icon_scaled.set_alpha(80)
    screen.blit(icon_scaled, icon_scaled.get_rect(center=(cx, cy)))


def draw_button_tooltip(screen, rect, text):
    tooltip      = small_font.render(text, True, (255, 255, 255))
    tooltip_rect = tooltip.get_rect(centerx=rect.centerx, bottom=rect.top - 8)
    padding_x, padding_y = 12, 6
    bg_rect = tooltip_rect.inflate(padding_x * 2, padding_y * 2)
    bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
    bg.fill((30, 30, 30, 230))
    pygame.draw.rect(bg, (100, 100, 100), (0, 0, bg_rect.width, bg_rect.height), 1)
    screen.blit(bg, bg_rect)
    screen.blit(tooltip, tooltip_rect)


clock      = pygame.time.Clock()
running    = True
show_help  = False

resize_pending = False
pending_width  = 0
pending_height = 0
resize_timer   = 0
RESIZE_DELAY   = 15

button_tooltips = {
    'io':      "IO Chain (O)",
    'size':    "Board Size (1/2/3)",
    'clear':   "Clear Solver (C) / All (Shift+C)",
    'solve':   "Solve (S)",
    'credits': "Credits (F2)",
}

while running:
    force_topmost()

    # ── Resize snap ──────────────────────────────────────────────────────────
    if resize_pending:
        resize_timer += 1
        if resize_timer >= RESIZE_DELAY:
            resize_pending = False
            resize_timer   = 0
            new_w, new_h = snap_window_size(pending_width, pending_height)
            if new_w != WINDOW_WIDTH or new_h != WINDOW_HEIGHT:
                WINDOW_WIDTH, WINDOW_HEIGHT = new_w, new_h
                screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), FLAGS)
                scale = WINDOW_WIDTH / BASE_WIDTH
                board.scale_x = scale
                board.scale_y = scale
                recompute_button_rects()

    # ── Background ───────────────────────────────────────────────────────────
    if bg_image:
        scaled_bg = pygame.transform.smoothscale(bg_image, (WINDOW_WIDTH, WINDOW_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
    else:
        screen.fill((0, 0, 0))

    # ── Tick size flash ─────────────────────────────────────────────────────
    if size_flash_frames > 0:
        size_flash_frames -= 1

    # ── Events ───────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            pending_width, pending_height = event.w, event.h
            WINDOW_WIDTH, WINDOW_HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), FLAGS)
            scale = min(WINDOW_WIDTH / BASE_WIDTH, WINDOW_HEIGHT / BASE_HEIGHT)
            board.scale_x = scale
            board.scale_y = scale
            recompute_button_rects()
            resize_pending = True
            resize_timer   = 0

        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            if event.key == pygame.K_h:
                show_help = not show_help
                continue
            if event.key == pygame.K_F2:
                board.toggle_credits()
                continue
            if event.key == pygame.K_ESCAPE:
                if show_help:
                    show_help = False
                elif getattr(board, "show_credits", False):
                    board.toggle_credits()
                elif board.selected_aspect:
                    board.deselect_aspect()
                else:
                    running = False
                continue

            if getattr(board, "show_credits", False):
                continue

            if board.solve_running:
                continue

            if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                board.undo()
            elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                board.redo()
            elif event.key == pygame.K_s and not (mods & pygame.KMOD_CTRL):
                board.solve_board()
            elif event.key == pygame.K_c and not (mods & pygame.KMOD_CTRL):
                if mods & pygame.KMOD_SHIFT:
                    board.clear_all()
                else:
                    board.clear_board()
            elif event.key == pygame.K_o:
                board.toggle_oi_chaining()
            elif event.key == pygame.K_1:
                if board.ring_count != 2:
                    board.save_state()
                    board.ring_count = 2
                    board.generate_grid()
                    board.set_status("Board size: 2 rings")
                    size_flash_frames = 10
            elif event.key == pygame.K_2:
                if board.ring_count != 3:
                    board.save_state()
                    board.ring_count = 3
                    board.generate_grid()
                    board.set_status("Board size: 3 rings")
                    size_flash_frames = 10
            elif event.key == pygame.K_3:
                if board.ring_count != 4:
                    board.save_state()
                    board.ring_count = 4
                    board.generate_grid()
                    board.set_status("Board size: 4 rings")
                    size_flash_frames = 10
            elif event.key == pygame.K_t:
                board.toggle_tooltips()

        elif event.type == pygame.MOUSEBUTTONDOWN and not show_help:
            mx, my = event.pos

            if event.button == 1 and credits_button and credits_button.collidepoint(mx, my):
                board.toggle_credits()
                continue

            if getattr(board, "show_credits", False):
                continue

            if board.solve_running:
                continue

            if event.button == 1:
                if io_button.collidepoint(mx, my):
                    board.toggle_oi_chaining()
                elif size_button.collidepoint(mx, my):
                    board.cycle_board_size()
                    size_flash_frames = 10  # flash on click
                elif clear_button.collidepoint(mx, my):
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        board.clear_all()
                    else:
                        board.clear_board()
                elif solve_button.collidepoint(mx, my):
                    board.solve_board()
                else:
                    clicked_sidebar = board.sidebar_click(mx, my)
                    if not clicked_sidebar:
                        pos = board.get_hex_at_pixel(mx, my)
                        if pos:
                            board.place_aspect(pos)

            elif event.button == 3:
                pos = board.get_hex_at_pixel(mx, my)
                if pos:
                    cell = board.grid[pos]
                    if cell['aspect']:
                        board.clear_aspect(pos)
                    else:
                        board.toggle_void(pos)
                else:
                    board.deselect_aspect()

    # ── Draw board and sidebars ──────────────────────────────────────────────
    board.draw(screen, font)
    board.draw_sidebars(screen, font)

    # ── Buttons ──────────────────────────────────────────────────────────────
    mx, my = pygame.mouse.get_pos()
    hovered_button = None

    if io_button.collidepoint(mx, my):
        hovered_button = 'io'
    elif size_button.collidepoint(mx, my):
        hovered_button = 'size'
    elif clear_button.collidepoint(mx, my):
        hovered_button = 'clear'
    elif solve_button.collidepoint(mx, my):
        hovered_button = 'solve'
    elif credits_button and credits_button.collidepoint(mx, my):
        hovered_button = 'credits'

    solve_active = not board.solve_running

    if IO_CENTER_IMG:
        draw_centered_icon(
            io_button,
            IO_CENTER_IMG,
            active=board.oi_chaining and not board.show_credits,
            scale_mult=1.8,
        )
    if hovered_button == 'io' and not board.solve_running and not board.show_credits:
        draw_button_tooltip(screen, io_button, button_tooltips['io'])

    if SIZE_IMG_1:
        flash = size_flash_frames > 0
        size_icon = SIZE_IMG_1
        if hovered_button == 'size' and not board.solve_running and not board.show_credits:
            if SIZE_IMG_2:
                size_icon = SIZE_IMG_2
        elif flash and SIZE_IMG_2:
            size_icon = SIZE_IMG_2

        draw_centered_icon(
            size_button,
            size_icon,
            active=solve_active and not board.show_credits,
            scale_mult=1.5,
        )
    if hovered_button == 'size' and not board.solve_running and not board.show_credits:
        draw_button_tooltip(screen, size_button, button_tooltips['size'])

    if CLEAR_IMG:
        draw_centered_icon(clear_button, CLEAR_IMG,
                           active=solve_active and not board.show_credits,
                           scale_mult=1.3)
    if hovered_button == 'clear' and not board.solve_running and not board.show_credits:
        draw_button_tooltip(screen, clear_button, button_tooltips['clear'])

    if SOLVE_IMG:
        if board.solve_running:
            draw_centered_icon(solve_button, SOLVE_IMG,
                               active=True, scale_mult=1.5)
        else:
            draw_centered_icon(solve_button, SOLVE_IMG,
                               active=not board.show_credits, scale_mult=1.3)
    if hovered_button == 'solve' and not board.solve_running and not board.show_credits:
        draw_button_tooltip(screen, solve_button, button_tooltips['solve'])

    if credits_button:
        base_color = (30, 30, 30)
        if hovered_button == 'credits':
            base_color = (45, 45, 45)
        border_color = (100, 100, 100)

        pygame.draw.rect(screen, base_color, credits_button)
        pygame.draw.rect(screen, border_color, credits_button, 1)

        label = small_font.render("Credits", True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=credits_button.center))

        if hovered_button == 'credits' and not board.show_credits:
            draw_button_tooltip(screen, credits_button, button_tooltips['credits'])

    # ── Overlays ─────────────────────────────────────────────────────────────
    if show_help:
        draw_help_overlay(screen)

    if getattr(board, "show_credits", False):
        board._draw_credits_overlay(screen, font)

    pygame.display.flip()
    clock.tick(60)

# ── Save config and exit ─────────────────────────────────────────────────────

if board.solve_running and board._solve_thread:
    board._solve_thread.join(timeout=3.0)

config["window_width"]  = WINDOW_WIDTH
config["window_height"] = WINDOW_HEIGHT
config["ring_count"]    = board.ring_count
config["oi_chaining"]   = board.oi_chaining
config["show_tooltips"] = board.show_tooltips
config["show_coords"]   = board.show_coords
save_config(config)

pygame.quit()