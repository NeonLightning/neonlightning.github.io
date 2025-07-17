import pygame
import os
import sys
import argparse
import tkinter as tk
from tkinter import filedialog
from collections import defaultdict
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

pygame.init()

def get_max_image_resolution(folder):
    max_res = 0
    supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')

    for filename in os.listdir(folder):
        if filename.lower().endswith(supported_exts):
            path = os.path.join(folder, filename)
            try:
                with Image.open(path) as img:
                    width, height = img.size
                    max_res = max(max_res, width, height)
            except Exception as e:
                print(f"Failed to read {filename}: {e}")
                continue
    return max_res if max_res > 0 else 10

MAX_HEADER_HEIGHT = 200
MAX_FILENAME_WIDTH = 200
MIN_HEADER_HEIGHT = 1
MIN_FILENAME_WIDTH = 1
BACKGROUND_COLOR = (30, 30, 30)
GRID_COLOR = (60, 60, 60)
HEADER_COLOR = (50, 50, 70)
TEXT_COLOR = (220, 220, 220)
PLACEHOLDER_COLOR = (80, 40, 40)
FULLSCREEN_BG = (0, 0, 0, 200)
CELL_PADDING = 5
FONT_SIZE = 14
RESOLUTION_FONT_SIZE = 12
ZOOM_SPEED = 0.05
MIN_START_ZOOM = 0.5
MIN_ZOOM = 0.05
MAX_ZOOM = 3.0
SCROLL_SPEED = 30
BUFFER_ROWS = 2
BUFFER_COLS = 2
INFO_HEIGHT = 30
EXPORT_BUTTON_COLOR = (60, 100, 180)
EXPORT_BUTTON_HOVER = (80, 120, 220)
HTML_BUTTON_COLOR = (60, 180, 100)
HTML_BUTTON_HOVER = (80, 220, 120)
MIN_TEXT_CELL_WIDTH = 1
MIN_TEXT_CELL_HEIGHT = 1

class ImageGrid:
    def __init__(self, base_folder, subfolders_dir):
        self.subfolders_dir = subfolders_dir
        self.base_folder = base_folder
        self.grid = self.build_grid()
        self.image_cache = {}
        self.cell_size = DEFAULT_CELL_SIZE
        self.zoom_level = 1.0
        self.scroll_offset = [0, 0]
        self.font = pygame.font.SysFont(None, FONT_SIZE)
        self.fullscreen_image = None
        self.fullscreen_rect = None
        self.fullscreen_original = None
        self.drag_start_pos = None
        self.drag_threshold = 5
        self.max_rows = len(self.grid)
        self.max_cols = max(len(row) for row in self.grid.values()) if self.grid else 0
        self.update_cell_sizes()
        self.base_resolution = self.get_base_resolution()
        self.reset_viewport()

    def reset_viewport(self):
        self.zoom_level = 1.0
        self.cell_size = DEFAULT_CELL_SIZE
        screen_width, screen_height = pygame.display.get_surface().get_size()
        visible_cols = screen_width // self.cell_size
        visible_rows = (screen_height - INFO_HEIGHT) // self.cell_size
        if visible_cols < 3 or visible_rows < 3:
            required_zoom = max(
                MIN_START_ZOOM,
                min(
                    (screen_width / 3) / DEFAULT_CELL_SIZE,
                    ((screen_height - INFO_HEIGHT) / 3) / DEFAULT_CELL_SIZE
                )
            )
            self.zoom_level = required_zoom
            self.cell_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
        self.scroll_offset = [0, 0]
        self.update_cell_sizes()

    def get_base_resolution(self):
        for f in os.listdir(self.base_folder):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                try:
                    path = os.path.join(self.base_folder, f)
                    with Image.open(path) as img:
                        return f"{img.width}×{img.height}"
                except:
                    continue
        return "Unknown"

    def build_grid(self):
        grid = defaultdict(list)
        base_images = []
        for f in os.listdir(self.base_folder):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                base_images.append(f)
        if not base_images:
            print(f"No images found in base folder: {self.base_folder}")
            return {}
        folders = []
        for base_img in sorted(base_images):
            folder_name = os.path.splitext(base_img)[0]
            folder_path = os.path.join(self.subfolders_dir, folder_name)
            folders.append((base_img, folder_path))
        all_filenames = set()
        for base_img, folder_path in folders:
            if os.path.isdir(folder_path):
                for f in os.listdir(folder_path):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                        all_filenames.add(f)
        sorted_filenames = sorted(all_filenames)
        grid[0] = [""]
        for base_img, folder_path in folders:
            folder_name = os.path.basename(folder_path)
            grid[0].append(folder_name)
        grid[1] = ["Base Images"]
        for base_img, folder_path in folders:
            grid[1].append(os.path.join(self.base_folder, base_img))
        for row_idx, filename in enumerate(sorted_filenames, start=2):
            grid[row_idx] = [filename]
            for base_img, folder_path in folders:
                img_path = os.path.join(folder_path, filename)
                if os.path.isfile(img_path):
                    grid[row_idx].append(img_path)
                else:
                    grid[row_idx].append(f"PLACEHOLDER:Image not found in {os.path.basename(folder_path)}")
        return dict(grid)

    def get_visible_cells(self, screen_width, screen_height):
        view_height = screen_height - INFO_HEIGHT
        start_row = max(0, int(self.scroll_offset[1] / self.cell_size))
        end_row = min(self.max_rows, 
                     int((self.scroll_offset[1] + view_height) / self.cell_size) + BUFFER_ROWS)
        start_col = max(0, int(self.scroll_offset[0] / self.cell_size))
        end_col = min(self.max_cols, 
                    int((self.scroll_offset[0] + screen_width) / self.cell_size) + BUFFER_COLS)
        return start_row, end_row, start_col, end_col

    def load_image(self, path):
        if isinstance(path, str) and path.startswith("PLACEHOLDER:"):
            placeholder = pygame.Surface((100, 100))
            placeholder.fill(PLACEHOLDER_COLOR)
            font = pygame.font.SysFont(None, 16)
            text = font.render(path.split(":", 1)[1].split(" at ")[0], True, (255, 255, 255))
            placeholder.blit(text, (10, 40))
            return placeholder
        if path not in self.image_cache:
            try:
                img = pygame.image.load(path)
                self.image_cache[path] = img
                return img
            except Exception as e:
                print(f"Error loading image {path}: {e}")
                placeholder = pygame.Surface((100, 100))
                placeholder.fill((120, 40, 40))
                font = pygame.font.SysFont(None, 16)
                text = font.render("Error", True, (255, 255, 255))
                placeholder.blit(text, (10, 40))
                self.image_cache[path] = placeholder
                return placeholder
        return self.image_cache[path]

    def unload_distant_images(self, visible_cells):
        start_row, end_row, start_col, end_col = visible_cells
        visible_paths = set()
        for row in range(start_row, end_row + 1):
            if row in self.grid:
                for col in range(start_col, min(end_col + 1, len(self.grid[row]))): 
                    visible_paths.add(self.grid[row][col])
        for path in list(self.image_cache.keys()):
            if path not in visible_paths and path != self.fullscreen_image:
                del self.image_cache[path]

    def draw_wrapped_text(self, surface, text, rect, font, color):
        if not text or not text.strip():
            return

        line_height = font.get_height()
        max_width = rect.width - 10
        max_lines = max(1, (rect.height - 10) // line_height)
        ellipsis = '...'
        ellipsis_width = font.size(ellipsis)[0]
        lines = []
        remaining_text = text.strip()
        while remaining_text and len(lines) < max_lines:
            low = 0
            high = len(remaining_text)
            best = ""
            while low <= high:
                mid = (low + high) // 2
                test_text = remaining_text[:mid]
                test_width = font.size(test_text)[0]
                if test_width <= max_width:
                    best = test_text
                    low = mid + 1
                else:
                    high = mid - 1
            if not best:
                best = ""
                for i in range(len(remaining_text), 0, -1):
                    test_text = remaining_text[:i] + ellipsis
                    if font.size(test_text)[0] <= max_width:
                        best = test_text
                        break
                if not best:
                    best = ellipsis if font.size(ellipsis)[0] <= max_width else ""
            if best:
                if ' ' in best and len(best) < len(remaining_text):
                    last_space = best.rfind(' ')
                    if last_space > 0:
                        candidate = best[:last_space]
                        if font.size(candidate)[0] <= max_width:
                            best = candidate
                lines.append(best)
                remaining_text = remaining_text[len(best):].lstrip()
            else:
                break
        if remaining_text and len(lines) == max_lines:
            last_line = lines[-1]
            if font.size(last_line)[0] + ellipsis_width <= max_width:
                lines[-1] = last_line + ellipsis
            else:
                while last_line and font.size(last_line[:-1] + ellipsis)[0] > max_width:
                    last_line = last_line[:-1]
                lines[-1] = last_line + ellipsis
        y = rect.top
        for line in lines:
            text_surface = font.render(line, True, color)
            surface.blit(text_surface, (rect.left + 5, y))
            y += line_height

    def update_cell_sizes(self):
        zoomed_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
        self.col_widths = []
        for col in range(self.max_cols):
            if col == 0:
                w = max(MIN_TEXT_CELL_WIDTH, 
                    min(MAX_FILENAME_WIDTH, 
                        max(MIN_FILENAME_WIDTH, zoomed_size)))
            else:
                w = zoomed_size
            self.col_widths.append(w)
        self.row_heights = []
        for row in range(self.max_rows):
            if row == 0:
                h = max(MIN_TEXT_CELL_HEIGHT,
                    min(MAX_HEADER_HEIGHT,
                        max(MIN_HEADER_HEIGHT, zoomed_size)))
            else:
                h = zoomed_size
            self.row_heights.append(h)

    def draw(self, screen):
        if self.fullscreen_image:
            self.draw_fullscreen(screen)
            return None, None
        screen_width, screen_height = screen.get_size()
        visible_cells = self.get_visible_cells(screen_width, screen_height)
        start_row, end_row, start_col, end_col = visible_cells
        grid_area = pygame.Rect(0, INFO_HEIGHT, screen_width, screen_height - INFO_HEIGHT)
        screen.fill(BACKGROUND_COLOR, grid_area)
        col_positions = [0]
        for w in self.col_widths[:-1]:
            col_positions.append(col_positions[-1] + w)
        row_positions = [INFO_HEIGHT]
        for h in self.row_heights[:-1]:
            row_positions.append(row_positions[-1] + h)
        for row in range(max(1, start_row), end_row + 1):
            if row not in self.grid:
                continue
            for col in range(max(1, start_col), min(end_col + 1, len(self.grid[row]))): 
                path = self.grid[row][col]
                img = self.load_image(path)
                x = col_positions[col] - self.scroll_offset[0]
                y = row_positions[row] - self.scroll_offset[1]
                w = self.col_widths[col]
                h = self.row_heights[row]
                if x + w < 0 or y + h < INFO_HEIGHT:
                    continue
                if x > screen_width or y > screen_height:
                    continue
                cell_rect = pygame.Rect(x, y, w, h)
                if isinstance(path, str) and path.startswith("PLACEHOLDER:"):
                    pygame.draw.rect(screen, PLACEHOLDER_COLOR, cell_rect)
                else:
                    pygame.draw.rect(screen, GRID_COLOR, cell_rect)
                pygame.draw.rect(screen, (100, 100, 100), cell_rect, 1)
                scaled_size = (max(1, w - CELL_PADDING * 2), max(1, h - CELL_PADDING * 2))
                try:
                    scaled_img = pygame.transform.scale(img, scaled_size)
                    screen.blit(scaled_img, (x + CELL_PADDING, y + CELL_PADDING))
                except:
                    pygame.draw.rect(screen, (120, 40, 40), 
                                (x + CELL_PADDING, y + CELL_PADDING, 
                                scaled_size[0], scaled_size[1]))
        if 0 in self.grid:
            y = INFO_HEIGHT
            h = self.row_heights[0]
            for col in range(max(0, start_col), min(end_col + 1, len(self.grid[0]))):
                text = self.grid[0][col]
                x = col_positions[col] - self.scroll_offset[0]
                w = self.col_widths[col]
                if x + w < 0 or x > screen_width:
                    continue
                header_rect = pygame.Rect(x, y, w, h)
                pygame.draw.rect(screen, HEADER_COLOR, header_rect)
                pygame.draw.rect(screen, (100, 100, 100), header_rect, 1)
                if col == 0:
                    display_text = "Filenames"
                else:
                    display_text = text
                if display_text:
                    text_rect = pygame.Rect(x + 5, y + 5, w - 10, h - 10)
                    self.draw_wrapped_text(screen, display_text, text_rect, self.font, TEXT_COLOR)
        for row in range(max(1, start_row), min(end_row + 1, self.max_rows)):
            if row not in self.grid:
                continue
            filename = self.grid[row][0]
            x = 0
            y = row_positions[row] - self.scroll_offset[1]
            w = self.col_widths[0]
            h = self.row_heights[row]
            if y + h < INFO_HEIGHT or y > screen_height:
                continue
            filename_rect = pygame.Rect(x, y, w, h)
            pygame.draw.rect(screen, HEADER_COLOR, filename_rect)
            pygame.draw.rect(screen, (100, 100, 100), filename_rect, 1)
            text_rect = pygame.Rect(x + 5, y + 5, w - 10, h - 10)
            self.draw_wrapped_text(screen, filename, text_rect, self.font, TEXT_COLOR)
        top_bar = pygame.Surface((screen_width, INFO_HEIGHT))
        top_bar.fill((20, 20, 20))
        screen.blit(top_bar, (0, 0))
        info = f"Base: {os.path.basename(self.base_folder)} | Zoom: {self.zoom_level:.1f}x | Rows: {self.max_rows} | Columns: {self.max_cols} | Cells: {sum(len(r) for r in self.grid.values())}"
        text = self.font.render(info, True, TEXT_COLOR)
        screen.blit(text, (10, 5))
        button_width = 110
        button_spacing = 10
        html_button_rect = pygame.Rect(screen_width - button_width - button_spacing - button_width, 5, button_width, 20)
        mouse_pos = pygame.mouse.get_pos()
        html_button_color = HTML_BUTTON_HOVER if html_button_rect.collidepoint(mouse_pos) else HTML_BUTTON_COLOR
        pygame.draw.rect(screen, html_button_color, html_button_rect, border_radius=5)
        html_button_text = self.font.render("Export HTML (H)", True, (255, 255, 255))
        screen.blit(html_button_text, (html_button_rect.x + 5, 7))
        export_button_rect = pygame.Rect(screen_width - button_width, 5, button_width, 20)
        export_button_color = EXPORT_BUTTON_HOVER if export_button_rect.collidepoint(mouse_pos) else EXPORT_BUTTON_COLOR
        pygame.draw.rect(screen, export_button_color, export_button_rect, border_radius=5)
        export_button_text = self.font.render("Export PNG (E)", True, (255, 255, 255))
        screen.blit(export_button_text, (export_button_rect.x + 5, 7))
        corner_rect = pygame.Rect(0, INFO_HEIGHT, self.col_widths[0], self.row_heights[0])
        pygame.draw.rect(screen, BACKGROUND_COLOR, corner_rect)
        pygame.draw.rect(screen, (100, 100, 100), corner_rect, 1)
        if self.base_resolution:
            res_font = pygame.font.SysFont(None, RESOLUTION_FONT_SIZE)
            text1 = res_font.render(self.base_resolution, True, (180, 180, 180))
            current_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
            text2 = res_font.render(f"{current_size}px", True, (180, 180, 180))
            total_height = text1.get_height() + text2.get_height()
            y_start = corner_rect.centery - total_height // 2
            text1_rect = text1.get_rect(centerx=corner_rect.centerx, top=y_start)
            text2_rect = text2.get_rect(centerx=corner_rect.centerx, top=y_start + text1.get_height())
            screen.blit(text1, text1_rect)
            screen.blit(text2, text2_rect)
        self.draw_scrollbars(screen, screen_width, screen_height)
        self.unload_distant_images(visible_cells)
        return export_button_rect, html_button_rect

    def draw_fullscreen(self, screen):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill(FULLSCREEN_BG)
        screen.blit(overlay, (0, 0))
        if self.fullscreen_original:
            screen_width, screen_height = screen.get_size()
            img_width, img_height = self.fullscreen_original.get_size()
            scale = min(screen_width / img_width, screen_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            x = (screen_width - new_width) // 2
            y = (screen_height - new_height) // 2
            scaled_img = pygame.transform.scale(self.fullscreen_original, (new_width, new_height))
            screen.blit(scaled_img, (x, y))
            row_name = "Unknown"
            col_name = "Unknown"
            for row_idx, row_data in self.grid.items():
                for col_idx, cell_value in enumerate(row_data):
                    if cell_value == self.fullscreen_image:
                        if row_idx in self.grid and len(self.grid[row_idx]) > 0:
                            row_name = self.grid[row_idx][0]
                        if 0 in self.grid and col_idx < len(self.grid[0]):
                            col_name = self.grid[0][col_idx]
                        break
            row_text = self.font.render(f"Row: {row_name}", True, (255, 255, 255))
            col_text = self.font.render(f"Column: {col_name}", True, (255, 255, 255))
            help_text = self.font.render("Click to exit fullscreen", True, (200, 200, 200))
            padding = 10
            box_width = max(row_text.get_width(), col_text.get_width()) + 2*padding
            box_height = row_text.get_height() + col_text.get_height() + 3*padding
            box_y = screen_height - box_height - help_text.get_height() - 20
            info_box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            info_box.fill((0, 0, 0, 100))
            info_box.blit(row_text, (padding, padding))
            info_box.blit(col_text, (padding, row_text.get_height() + 2*padding))
            screen.blit(info_box, (padding, box_y))
            help_box_width = help_text.get_width() + 2*padding
            help_box = pygame.Surface((help_box_width, help_text.get_height() + 2*padding), pygame.SRCALPHA)
            help_box.fill((0, 0, 0, 100))
            help_box.blit(help_text, (padding, padding))
            screen.blit(help_box, (screen_width//2 - help_box_width//2, screen_height - help_text.get_height() - 2*padding))

    def draw_scrollbars(self, screen, screen_width, screen_height):
        if self.max_rows > 0:
            max_scroll_y = self.max_rows * self.cell_size - (screen_height - INFO_HEIGHT)
            if max_scroll_y > 0:
                scroll_y = self.scroll_offset[1] / max_scroll_y
                scroll_y = max(0, min(1, scroll_y))
                scrollbar_height = max(10, (screen_height - INFO_HEIGHT) * 0.1)
                scrollbar_pos = scroll_y * (screen_height - INFO_HEIGHT - scrollbar_height) + INFO_HEIGHT
                pygame.draw.rect(screen, (100, 100, 100), (screen_width - 10, INFO_HEIGHT, 10, screen_height - INFO_HEIGHT))
                pygame.draw.rect(screen, (200, 200, 200), 
                               (screen_width - 10, scrollbar_pos, 10, scrollbar_height))
        if self.max_cols > 0:
            max_scroll_x = self.max_cols * self.cell_size - screen_width
            if max_scroll_x > 0:
                scroll_x = self.scroll_offset[0] / max_scroll_x
                scroll_x = max(0, min(1, scroll_x))
                scrollbar_width = max(10, screen_width * 0.1)
                scrollbar_pos = scroll_x * (screen_width - scrollbar_width)
                pygame.draw.rect(screen, (100, 100, 100), (0, screen_height - 10, screen_width, 10))
                pygame.draw.rect(screen, (200, 200, 200), 
                               (scrollbar_pos, screen_height - 10, scrollbar_width, 10))

    def zoom(self, direction, mouse_pos=None):
        if self.fullscreen_image:
            return
        old_zoom = self.zoom_level
        self.zoom_level = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom_level + direction * ZOOM_SPEED))
        self.update_cell_sizes()
        if mouse_pos:
            grid_x = (self.scroll_offset[0] + mouse_pos[0]) / (self.cell_size)
            grid_y = (self.scroll_offset[1] + mouse_pos[1] - INFO_HEIGHT) / (self.cell_size)
            self.cell_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
            self.scroll_offset[0] = grid_x * self.cell_size - mouse_pos[0]
            self.scroll_offset[1] = grid_y * self.cell_size - (mouse_pos[1] - INFO_HEIGHT)
        else:
            self.cell_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
        self.enforce_scroll_bounds(screen.get_size())

    def enforce_scroll_bounds(self, screen_size):
        if self.fullscreen_image:
            return
        screen_width, screen_height = screen_size
        max_scroll_x = max(0, self.max_cols * self.cell_size - screen_width)
        max_scroll_y = max(0, self.max_rows * self.cell_size - (screen_height - INFO_HEIGHT))
        self.scroll_offset[0] = max(0, min(max_scroll_x, self.scroll_offset[0]))
        self.scroll_offset[1] = max(0, min(max_scroll_y, self.scroll_offset[1]))

    def scroll(self, dx, dy):
        if self.fullscreen_image:
            return
        self.scroll_offset[0] += dx
        self.scroll_offset[1] += dy
        self.enforce_scroll_bounds(screen.get_size())

    def toggle_fullscreen(self, path):
        if self.fullscreen_image == path:
            self.fullscreen_image = None
            self.fullscreen_original = None
        else:
            self.fullscreen_image = path
            try:
                self.fullscreen_original = pygame.image.load(path)
            except:
                self.fullscreen_image = None
                self.fullscreen_original = None

    def export_grid(self, filename=None):
        def draw_wrapped_text_pil(draw, text, font, box, fill):
            x1, y1, x2, y2 = box
            max_width = x2 - x1 - 10
            max_height = y2 - y1 - 10
            lines = []
            words = text.split()
            if not words:
                return
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = font.getbbox(test_line)
                w = bbox[2] - bbox[0]
                if w <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            bbox = font.getbbox('A')
            line_height = bbox[3] - bbox[1]
            y_text = y1 + 5
            for line in lines:
                if y_text + line_height > y2:
                    break
                draw.text((x1 + 5, y_text), line, font=font, fill=fill)
                y_text += line_height
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"grid_export_{timestamp}.png"
        try:
            total_width = self.max_cols * self.cell_size
            total_height = self.max_rows * self.cell_size
            image = Image.new("RGB", (total_width, total_height), BACKGROUND_COLOR)
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("arial.ttf", FONT_SIZE)
            small_font = ImageFont.truetype("arial.ttf", RESOLUTION_FONT_SIZE)
            for row in range(self.max_rows):
                if row not in self.grid:
                    continue
                for col in range(len(self.grid[row])):
                    x = col * self.cell_size
                    y = row * self.cell_size
                    box = (x, y, x + self.cell_size, y + self.cell_size)
                    value = self.grid[row][col]
                    is_top = row == 0
                    is_base = row == 1
                    is_left = col == 0
                    if row == 0 and col == 0:
                        draw.rectangle(box, fill=BACKGROUND_COLOR)
                    elif is_top or is_left:
                        draw.rectangle(box, fill=HEADER_COLOR)
                    elif isinstance(value, str) and value.startswith("PLACEHOLDER:"):
                        draw.rectangle(box, fill=PLACEHOLDER_COLOR)
                    else:
                        draw.rectangle(box, fill=GRID_COLOR)
                    draw.rectangle(box, outline=(100, 100, 100))
                    if row == 0 or col == 0:
                        if row == 0 and col == 0:
                            if self.base_resolution:
                                current_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
                                bbox1 = small_font.getbbox(self.base_resolution)
                                bbox2 = small_font.getbbox(f"{current_size}px")
                                text1_width = bbox1[2] - bbox1[0]
                                text1_height = bbox1[3] - bbox1[1]
                                text2_width = bbox2[2] - bbox2[0]
                                text2_height = bbox2[3] - bbox2[1]
                                total_height = text1_height + text2_height
                                y_start = y + (self.cell_size - total_height) // 2
                                x_center1 = x + (self.cell_size - text1_width) // 2
                                draw.text((x_center1, y_start), self.base_resolution, 
                                         font=small_font, fill=TEXT_COLOR)
                                x_center2 = x + (self.cell_size - text2_width) // 2
                                draw.text((x_center2, y_start + text1_height), f"{current_size}px", 
                                         font=small_font, fill=TEXT_COLOR)
                            continue
                        text = "Base Images" if row == 1 and col == 0 else value
                        box = (x, y, x + self.cell_size, y + self.cell_size)
                        draw_wrapped_text_pil(draw, text, font, box, TEXT_COLOR)
                    elif isinstance(value, str) and not value.startswith("PLACEHOLDER:"):
                        try:
                            img = Image.open(value)
                            img = img.resize((self.cell_size - 2 * CELL_PADDING,
                                            self.cell_size - 2 * CELL_PADDING))
                            image.paste(img, (x + CELL_PADDING, y + CELL_PADDING))
                            img.close()
                        except Exception as e:
                            print(f"Image error at {value}: {e}")
            image.save(filename)
            return filename
        except Exception as e:
            print(f"Error exporting large grid: {e}")
            return None
        
    def export_html(self, output_folder="html_export"):
        try:
            os.makedirs(output_folder, exist_ok=True)
            images_dir = os.path.join(output_folder, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Updated HTML template with tooltip styles and JavaScript
            html_template = """<!DOCTYPE html>
    <html>
    <head>
        <title>Image Grid Export</title>
        <style>
            body {{
                background-color: #1e1e1e;
                color: #dcdcdc;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                margin-bottom: 20px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: {filename_width}px repeat({num_cols}, {cell_size}px);
                grid-gap: 1px;
                margin-bottom: 30px;
            }}
            .cell {{
                background-color: #3c3c3c;
                padding: 5px;
                overflow: hidden;
                text-align: center;
                border: 1px solid #646464;
                position: relative;
            }}
            .header {{
                background-color: #323246;
                font-weight: bold;
            }}
            .filename {{
                background-color: #323246;
                text-align: left;
                word-break: break-all;
            }}
            .placeholder {{
                background-color: #502828;
            }}
            img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }}
            .info {{
                margin-bottom: 20px;
                padding: 10px;
                background-color: #282828;
                border-radius: 5px;
            }}
            .tooltip {{
                visibility: hidden;
                width: 200px;
                background-color: #555;
                color: #fff;
                text-align: center;
                border-radius: 6px;
                padding: 5px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                margin-left: -100px;
                opacity: 0;
                transition: opacity 0.3s;
            }}
            .cell:hover .tooltip {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
    </head>
    <body>
        <div class="info">
            <h1>Image Grid Export</h1>
            <p>Base folder: {base_folder}</p>
            <p>Exported on: {timestamp}</p>
            <p>Grid size: {rows} rows × {cols} columns</p>
            <p>Cell size: {cell_size}px</p>
        </div>
        
        <div class="grid">
            {grid_content}
        </div>
    </body>
    </html>
    """
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cell_size = int(DEFAULT_CELL_SIZE * self.zoom_level)
            filename_width = max(MIN_FILENAME_WIDTH, min(MAX_FILENAME_WIDTH, cell_size))
            
            grid_content = []
            image_counter = 0
            
            # First pass to collect all row and column names
            row_names = {}
            col_names = {}
            
            for row in range(self.max_rows):
                if row not in self.grid:
                    continue
                if row >= 1 and len(self.grid[row]) > 0:
                    row_names[row] = self.grid[row][0]  # Column 0 contains row names
                    
            if 0 in self.grid:  # Row 0 contains column names
                for col, name in enumerate(self.grid[0]):
                    col_names[col] = name
            
            for row in range(self.max_rows):
                if row not in self.grid:
                    continue
                    
                for col in range(len(self.grid[row])):
                    value = self.grid[row][col]
                    cell_classes = ["cell"]
                    
                    if row == 0 or col == 0:
                        cell_classes.append("header")
                    if col == 0:
                        cell_classes.append("filename")
                    
                    content = ""
                    tooltip_content = ""
                    
                    # Set tooltip content based on position
                    if row == 0 and col == 0:
                        tooltip_content = "Grid Corner"
                    elif row == 0:
                        tooltip_content = f"Column: {col_names.get(col, '')}"
                    elif col == 0:
                        tooltip_content = f"Row: {row_names.get(row, '')}"
                    else:
                        tooltip_content = f"Row: {row_names.get(row, '')}<br>Column: {col_names.get(col, '')}"
                    
                    if isinstance(value, str):
                        if value.startswith("PLACEHOLDER:"):
                            cell_classes.append("placeholder")
                            content = value.split(":", 1)[1].split(" at ")[0]
                        elif row == 0 or col == 0:
                            content = value
                        else:
                            try:
                                img = Image.open(value)
                                img_filename = f"img_{image_counter}.webp"
                                img_path = os.path.join(images_dir, img_filename)
                                
                                target_size = cell_size - 2 * CELL_PADDING
                                width, height = img.size
                                ratio = min(target_size/width, target_size/height)
                                new_size = (int(width * ratio), (int(height * ratio)))
                                
                                img = img.resize(new_size, Image.Resampling.LANCZOS)
                                img.save(img_path, "WEBP", quality=85)
                                img.close()
                                
                                content = f'<img src="images/{img_filename}" alt="{os.path.basename(value)}">'
                                image_counter += 1
                            except Exception as e:
                                print(f"Error processing image {value}: {e}")
                                cell_classes.append("placeholder")
                                content = "Image Error"
                    
                    cell_html = f'''
                    <div class="{" ".join(cell_classes)}">
                        {content}
                        <span class="tooltip">{tooltip_content}</span>
                    </div>
                    '''
                    grid_content.append(cell_html)
            
            html_file = os.path.join(output_folder, "index.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_template.format(
                    base_folder=os.path.basename(self.base_folder),
                    timestamp=timestamp,
                    rows=self.max_rows,
                    cols=self.max_cols,
                    cell_size=cell_size,
                    filename_width=filename_width,
                    num_cols=self.max_cols - 1,
                    grid_content="\n".join(grid_content)
                ))
            
            return html_file
        
        except Exception as e:
            print(f"Error exporting HTML: {e}")
            return None

def select_folder(title="Select Folder"):
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title=title)
    root.destroy()
    return folder

def main():
    global screen, DEFAULT_CELL_SIZE

    parser = argparse.ArgumentParser(description='Image Grid Viewer')
    parser.add_argument('base_folder', nargs='?', help='Base folder containing images')
    parser.add_argument('subfolders_dir', nargs='?', help='Directory containing subfolders with comparison images')
    args = parser.parse_args()
    if args.base_folder:
        base_folder = args.base_folder
    else:
        base_folder = select_folder("Select Base Image Folder")
    if not base_folder or not os.path.isdir(base_folder):
        print("No valid base folder selected. Exiting.")
        return
    if args.subfolders_dir:
        subfolders_dir = args.subfolders_dir
    else:
        subfolders_dir = select_folder("Select Subfolders Directory")
    if not subfolders_dir or not os.path.isdir(subfolders_dir):
        print("No valid subfolders directory selected. Exiting.")
        return
    screen = pygame.display.set_mode((1024, 768), pygame.RESIZABLE)
    pygame.display.set_caption(f"Image Grid Viewer - {os.path.basename(base_folder)}")
    clock = pygame.time.Clock()
    DEFAULT_CELL_SIZE = get_max_image_resolution(base_folder)
    grid = ImageGrid(base_folder, subfolders_dir)
    grid.reset_viewport()
    grid.enforce_scroll_bounds(screen.get_size())
    pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, 
                                       {'w': screen.get_width(), 
                                        'h': screen.get_height()}))
    dragging = False
    last_mouse_pos = (0, 0)
    export_button_rect = None
    html_button_rect = None
    drag_start_pos = None
    while True:
        export_button_rect, html_button_rect = grid.draw(screen)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if grid.fullscreen_image:
                        grid.toggle_fullscreen(None)
                    else:
                        if export_button_rect and export_button_rect.collidepoint(event.pos):
                            filename = grid.export_grid()
                            if filename:
                                print(f"Grid exported to {filename}")
                        elif html_button_rect and html_button_rect.collidepoint(event.pos):
                            html_file = grid.export_html()
                            if html_file:
                                print(f"HTML exported to {html_file}")
                        else:
                            drag_start_pos = event.pos
                            dragging = True
                            last_mouse_pos = event.pos
                elif event.button == 4:
                    grid.zoom(1, event.pos)
                elif event.button == 5:
                    grid.zoom(-1, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and dragging:
                    if drag_start_pos and (
                        abs(event.pos[0] - drag_start_pos[0]) < grid.drag_threshold and 
                        abs(event.pos[1] - drag_start_pos[1]) < grid.drag_threshold
                    ):
                        mouse_pos = pygame.mouse.get_pos()
                        col_accum = 0
                        col_index = -1
                        for idx, width in enumerate(grid.col_widths):
                            col_accum += width
                            if mouse_pos[0] + grid.scroll_offset[0] < col_accum:
                                col_index = idx
                                break
                        row_accum = INFO_HEIGHT
                        row_index = -1
                        for idx, height in enumerate(grid.row_heights):
                            row_accum += height
                            if mouse_pos[1] + grid.scroll_offset[1] < row_accum:
                                row_index = idx
                                break
                        if (row_index >= 0 and col_index >= 0 and 
                            row_index in grid.grid and 
                            col_index < len(grid.grid[row_index]) and 
                            row_index >= 1 and
                            col_index >= 1):
                            path = grid.grid[row_index][col_index]
                            if not path.startswith("PLACEHOLDER:"):
                                grid.toggle_fullscreen(path)
                    dragging = False
                    drag_start_pos = None
            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    dx = last_mouse_pos[0] - event.pos[0]
                    dy = last_mouse_pos[1] - event.pos[1]
                    grid.scroll(dx, dy)
                    last_mouse_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    grid.scroll(0, SCROLL_SPEED)
                elif event.key == pygame.K_DOWN:
                    grid.scroll(0, -SCROLL_SPEED)
                elif event.key == pygame.K_LEFT:
                    grid.scroll(SCROLL_SPEED, 0)
                elif event.key == pygame.K_RIGHT:
                    grid.scroll(-SCROLL_SPEED, 0)
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    grid.zoom(1)
                elif event.key == pygame.K_MINUS:
                    grid.zoom(-1)
                elif event.key == pygame.K_h:
                    html_file = grid.export_html()
                    if html_file:
                        print(f"HTML exported to {html_file}")
                elif event.key == pygame.K_0:
                    grid.reset_viewport()
                    grid.enforce_scroll_bounds(screen.get_size())
                elif event.key == pygame.K_ESCAPE:
                    if grid.fullscreen_image:
                        grid.toggle_fullscreen(None)
                    else:
                        pygame.quit()
                        sys.exit()
                elif event.key == pygame.K_r:
                    grid = ImageGrid(base_folder)
                elif event.key == pygame.K_e:
                    filename = grid.export_grid()
                    if filename:
                        print(f"Grid exported to {filename}")
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                grid.enforce_scroll_bounds((event.w, event.h))
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()