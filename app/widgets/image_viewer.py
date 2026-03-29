"""In-app overlay image viewer with zoom, rotate, pan, and navigation."""

import os
import platform
import subprocess
from tkinter import Canvas

import customtkinter as ctk
from PIL import Image, ImageTk

from app.widgets.tooltip import ToolTip


class ImageViewerOverlay(ctk.CTkFrame):
    """An in-app overlay image viewer with zoom, rotate, pan, and navigation."""

    def __init__(self, parent_frame, app, image_list, start_index=0):
        super().__init__(parent_frame, fg_color="#1A1A1A", corner_radius=0)
        # Place as overlay covering the entire parent frame
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()

        self.app = app  # Reference to FaceApp for key bindings
        self.image_list = image_list
        self.current_index = start_index
        self.zoom_level = 1.0
        self.rotation = 0
        self.pan_x = 0
        self.pan_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._pil_image = None
        self._tk_photo = None
        self._key_bindings = []

        self._build_ui()
        self._bind_keys()
        self._load_current_image()
        # Defer the initial fit until the canvas is actually laid out
        self.after(50, self._fit_to_window)

    def _build_ui(self):
        # --- Top toolbar ---
        toolbar = ctk.CTkFrame(self, height=50, fg_color="#252525", corner_radius=0)
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        self.filename_lbl = ctk.CTkLabel(toolbar, text="", font=("Arial", 13), text_color="#CCCCCC", anchor="w")
        self.filename_lbl.pack(side="left", padx=15)

        btn_style = {"width": 36, "height": 32, "font": ("Arial", 16), "fg_color": "transparent",
                     "hover_color": "#3A3A3A", "text_color": "#DDDDDD", "corner_radius": 6}

        btn_close = ctk.CTkButton(toolbar, text="\u2715", command=self.close_viewer, **btn_style)
        btn_close.pack(side="right", padx=(0, 10))
        ToolTip(btn_close, "Close  (Esc)")

        btn_folder = ctk.CTkButton(toolbar, text="\ud83d\udcc2", command=self._open_file_location, **btn_style)
        btn_folder.pack(side="right", padx=2)
        ToolTip(btn_folder, "Open file location")

        btn_copy = ctk.CTkButton(toolbar, text="\ud83d\udccb", command=self._copy_path, **btn_style)
        btn_copy.pack(side="right", padx=2)
        ToolTip(btn_copy, "Copy file path")

        sep = ctk.CTkFrame(toolbar, width=1, height=24, fg_color="#444")
        sep.pack(side="right", padx=8)

        btn_rotate = ctk.CTkButton(toolbar, text="\u21bb", command=self._rotate_cw, **btn_style)
        btn_rotate.pack(side="right", padx=2)
        ToolTip(btn_rotate, "Rotate 90\u00b0  (R)")

        btn_fit = ctk.CTkButton(toolbar, text="\u22a1", command=self._fit_to_window, **btn_style)
        btn_fit.pack(side="right", padx=2)
        ToolTip(btn_fit, "Fit to window  (F)")

        btn_zin = ctk.CTkButton(toolbar, text="\uff0b", command=self._zoom_in, **btn_style)
        btn_zin.pack(side="right", padx=2)
        ToolTip(btn_zin, "Zoom in  (+)")

        btn_zout = ctk.CTkButton(toolbar, text="\uff0d", command=self._zoom_out, **btn_style)
        btn_zout.pack(side="right", padx=2)
        ToolTip(btn_zout, "Zoom out  (-)")

        self.zoom_lbl = ctk.CTkLabel(toolbar, text="100%", font=("Arial", 12), text_color="#888", width=50)
        self.zoom_lbl.pack(side="right", padx=4)

        # --- Bottom bar ---
        bottom_bar = ctk.CTkFrame(self, height=44, fg_color="#252525", corner_radius=0)
        bottom_bar.pack(fill="x", side="bottom")
        bottom_bar.pack_propagate(False)

        nav_frame = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        nav_frame.pack(expand=True)

        nav_btn_style = {"width": 80, "height": 30, "font": ("Arial", 13), "fg_color": "#333",
                         "hover_color": "#444", "text_color": "#DDD", "corner_radius": 6}

        self.prev_btn = ctk.CTkButton(nav_frame, text="\u25c0 Prev", command=self._prev_image, **nav_btn_style)
        self.prev_btn.pack(side="left", padx=8, pady=6)
        ToolTip(self.prev_btn, "Previous image  (\u2190)")

        self.counter_lbl = ctk.CTkLabel(nav_frame, text="1 / 1", font=("Arial", 13), text_color="#AAA", width=80)
        self.counter_lbl.pack(side="left", padx=10)

        self.next_btn = ctk.CTkButton(nav_frame, text="Next \u25b6", command=self._next_image, **nav_btn_style)
        self.next_btn.pack(side="left", padx=8, pady=6)
        ToolTip(self.next_btn, "Next image  (\u2192)")

        self.dims_lbl = ctk.CTkLabel(bottom_bar, text="", font=("Arial", 11), text_color="#666")
        self.dims_lbl.pack(side="right", padx=15)

        # --- Canvas ---
        self.canvas = Canvas(self, bg="#1A1A1A", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def _bind_keys(self):
        root = self.app
        bindings = [
            ("<Escape>", lambda e: self.close_viewer()),
            ("<Left>", lambda e: self._prev_image()),
            ("<Right>", lambda e: self._next_image()),
            ("<plus>", lambda e: self._zoom_in()),
            ("<equal>", lambda e: self._zoom_in()),
            ("<minus>", lambda e: self._zoom_out()),
            ("<r>", lambda e: self._rotate_cw()),
            ("<R>", lambda e: self._rotate_cw()),
            ("<f>", lambda e: self._fit_to_window()),
            ("<F>", lambda e: self._fit_to_window()),
            ("<Home>", lambda e: self._reset_view()),
        ]
        for seq, func in bindings:
            bid = root.bind(seq, func, add="+")
            self._key_bindings.append((seq, bid))

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<Configure>", lambda e: self._render_image())

    def _unbind_keys(self):
        root = self.app
        for seq, bid in self._key_bindings:
            root.unbind(seq, bid)
        self._key_bindings.clear()

    def close_viewer(self):
        """Close the overlay and return to the gallery."""
        self._unbind_keys()
        self.app._viewer_overlay = None
        self.destroy()

    # --- IMAGE LOADING ---
    def _load_current_image(self):
        path = self.image_list[self.current_index]
        self.zoom_level = 1.0
        self.rotation = 0
        self.pan_x = 0
        self.pan_y = 0

        try:
            self._pil_image = Image.open(path)
            self._pil_image.load()
        except (OSError, IOError):
            self._pil_image = None

        filename = os.path.basename(path)
        self.filename_lbl.configure(text=filename)
        self.counter_lbl.configure(text=f"{self.current_index + 1} / {len(self.image_list)}")

        if self._pil_image:
            w, h = self._pil_image.size
            self.dims_lbl.configure(text=f"{w} \u00d7 {h} px")
        else:
            self.dims_lbl.configure(text="Failed to load")

        self.prev_btn.configure(state="normal" if self.current_index > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_index < len(self.image_list) - 1 else "disabled")

        self._fit_to_window()

    # --- RENDERING ---
    def _render_image(self):
        self.canvas.delete("all")
        if not self._pil_image:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                text="Could not load image", fill="#FF5555", font=("Arial", 16)
            )
            return

        img = self._pil_image
        if self.rotation % 360 != 0:
            img = img.rotate(-self.rotation, expand=True, resample=Image.Resampling.BICUBIC)

        new_w = max(1, int(img.width * self.zoom_level))
        new_h = max(1, int(img.height * self.zoom_level))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        self._tk_photo = ImageTk.PhotoImage(img)

        cx = self.canvas.winfo_width() // 2 + self.pan_x
        cy = self.canvas.winfo_height() // 2 + self.pan_y
        self.canvas.create_image(cx, cy, image=self._tk_photo, anchor="center")

        self.zoom_lbl.configure(text=f"{int(self.zoom_level * 100)}%")

    # --- ZOOM ---
    def _zoom_in(self):
        self.zoom_level = min(10.0, self.zoom_level * 1.25)
        self._render_image()

    def _zoom_out(self):
        self.zoom_level = max(0.05, self.zoom_level / 1.25)
        self._render_image()

    def _on_mousewheel(self, event):
        if event.delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def _fit_to_window(self):
        if not self._pil_image:
            return
        self.pan_x = 0
        self.pan_y = 0

        img = self._pil_image
        if self.rotation % 360 != 0:
            img = img.rotate(-self.rotation, expand=True)

        cw = max(self.canvas.winfo_width(), 200)
        ch = max(self.canvas.winfo_height(), 200)
        padding = 40
        scale_w = (cw - padding) / img.width
        scale_h = (ch - padding) / img.height
        self.zoom_level = min(scale_w, scale_h, 1.0)
        self._render_image()

    def _reset_view(self):
        self.zoom_level = 1.0
        self.rotation = 0
        self.pan_x = 0
        self.pan_y = 0
        self._render_image()

    # --- ROTATE ---
    def _rotate_cw(self):
        self.rotation = (self.rotation + 90) % 360
        self._render_image()

    # --- PAN ---
    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_move(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._render_image()

    # --- NAVIGATION ---
    def _prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_image()

    def _next_image(self):
        if self.current_index < len(self.image_list) - 1:
            self.current_index += 1
            self._load_current_image()

    # --- FILE ACTIONS ---
    def _open_file_location(self):
        path = self.image_list[self.current_index]
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])

    def _copy_path(self):
        path = self.image_list[self.current_index]
        self.clipboard_clear()
        self.clipboard_append(os.path.normpath(path))
        original = self.filename_lbl.cget("text")
        self.filename_lbl.configure(text="\u2713 Path copied!", text_color="#00CC66")
        self.after(1500, lambda: self.filename_lbl.configure(text=original, text_color="#CCCCCC"))
