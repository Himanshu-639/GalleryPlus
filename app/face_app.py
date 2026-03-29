"""Main FaceApp UI class — sidebar, gallery, tabs, navigation."""

import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from app.config import THUMBS_DIR
from app.database import get_connection
from app.engine import process_single_image, process_with_cache, load_known_encodings
from app.widgets import ImageViewerOverlay


class FaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gallery+")
        self.geometry("1100x700")

        # State
        self.current_page = "images"
        self.current_tab = "images"
        self.current_person_view = None
        self.current_cols = 1
        self.is_scanning = False
        self.resize_timer = None
        self._detail_image_list = []
        self._sort_by = "name_asc"
        self._search_query = ""
        self._viewer_overlay = None

        # Image cache: maps (path, size) -> CTkImage
        self._image_cache = {}

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # UI Setup
        self._setup_sidebar()
        self._setup_main_area()

        self.show_images_tab()

    # ================================================================
    # SIDEBAR
    # ================================================================
    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="Gallery+", font=("Arial", 24, "bold")).grid(
            row=0, column=0, padx=20, pady=(30, 20))

        # Search bar
        self.search_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Search",
                                         height=36, font=("Arial", 13),
                                         fg_color="#2B2B2B", border_color="#444", corner_radius=8)
        self.search_entry.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        ctk.CTkButton(self.sidebar, text="+ Upload Image", height=40, font=("Arial", 14, "bold"),
                      fg_color="#1F6AA5", hover_color="#144870",
                      command=self.upload_image).grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.scan_btn = ctk.CTkButton(self.sidebar, text="\ud83d\udd0d Scan Storage", height=40,
                                      font=("Arial", 14, "bold"),
                                      fg_color="#2B8C58", hover_color="#1E613D",
                                      command=self.start_scan)
        self.scan_btn.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(self.sidebar, text="System Ready", text_color="gray", wraplength=200)
        self.status_label.grid(row=4, column=0, padx=20, pady=10)

        self.sidebar.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(self.sidebar, text="Gallery+ v2.0", text_color="#555").grid(row=6, column=0, pady=20)

    # ================================================================
    # MAIN AREA
    # ================================================================
    def _setup_main_area(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))

        # Header
        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(10, 0), padx=(10, 20))

        self.header_lbl = ctk.CTkLabel(self.header_frame, text="", font=("Arial", 28, "bold"), anchor="w")

        # Tab buttons
        self.tab_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        tab_btn_style = {"height": 40, "font": ("Arial", 15, "bold"), "corner_radius": 8, "border_width": 0}

        self.images_tab_btn = ctk.CTkButton(self.tab_frame, text="\ud83d\udcf7  Images",
                                            command=self.show_images_tab, **tab_btn_style)
        self.images_tab_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.faces_tab_btn = ctk.CTkButton(self.tab_frame, text="\ud83d\udc64  Faces",
                                           command=self.show_faces_tab, **tab_btn_style)
        self.faces_tab_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.back_btn = ctk.CTkButton(self.header_frame, text="\u2190 Back", width=80, fg_color="transparent",
                                      border_width=1, text_color="#DDD", hover_color="#333",
                                      command=self._go_back)

        # Sort bar
        self.sort_bar = ctk.CTkFrame(self.main_area, fg_color="transparent", height=36)

        self.image_count_lbl = ctk.CTkLabel(self.sort_bar, text="", font=("Arial", 12), text_color="#666")
        self.image_count_lbl.pack(side="left", padx=(12, 6))

        sort_options = ["Name (A-Z)", "Name (Z-A)", "Date (Newest)", "Date (Oldest)",
                        "Size (Largest)", "Size (Smallest)"]
        self.sort_menu = ctk.CTkOptionMenu(
            self.sort_bar, values=sort_options, width=150, height=28,
            font=("Arial", 12), fg_color="#333", button_color="#444",
            button_hover_color="#555", dropdown_fg_color="#333",
            command=self._on_sort_changed)
        self.sort_menu.set("Name (A-Z)")
        self.sort_menu.pack(side="right", padx=(4, 15))

        sort_lbl = ctk.CTkLabel(self.sort_bar, text="Sort by:", font=("Arial", 12), text_color="#888")
        sort_lbl.pack(side="right", padx=(0, 4))

        # Gallery
        self.gallery_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent", corner_radius=0)
        self._boost_scroll_speed(self.gallery_frame)
        self.main_area.bind("<Configure>", self.check_resize)

    def _boost_scroll_speed(self, scrollable_frame):
        """Boost mousewheel scrolling speed globally."""
        canvas = scrollable_frame._parent_canvas
        canvas.configure(yscrollincrement=25)

        def _fast_scroll(event):
            if not canvas.winfo_ismapped():
                return
            delta = -8 if event.delta > 0 else 8
            canvas.yview_scroll(delta, "units")
            return "break"

        self.bind_all("<MouseWheel>", _fast_scroll)

    # ================================================================
    # HELPERS
    # ================================================================
    def _load_image(self, path, size=(150, 150)):
        """Load and cache an image thumbnail."""
        cache_key = (path, size)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        try:
            pil_img = Image.open(path)
            pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
            self._image_cache[cache_key] = ctk_img
            return ctk_img
        except (OSError, IOError, ValueError):
            return None

    def _create_card(self, row, col, img_path, name=None, is_person_card=False, img_index=None):
        card = ctk.CTkFrame(self.gallery_frame, width=170, height=200 if is_person_card else 170,
                            corner_radius=0, fg_color="#2B2B2B")
        card.grid(row=row, column=col, padx=8, pady=8)
        card.grid_propagate(False)

        display_image = self._load_image(img_path) if img_path else None

        if display_image:
            lbl = ctk.CTkLabel(card, image=display_image, text="", cursor="hand2")
            lbl.pack(pady=(10, 0) if is_person_card else 0, expand=True)
            if is_person_card:
                lbl.bind("<Button-1>", lambda e, n=name: self.show_person_detail(n))
            elif img_index is not None:
                lbl.bind("<Button-1>", lambda e, idx=img_index: self._open_image_viewer(idx))
        else:
            ctk.CTkLabel(card, text="File Missing").pack(
                pady=(10, 0) if is_person_card else 0, expand=True)

        if is_person_card:
            name_var = ctk.StringVar(value=name)
            entry = ctk.CTkEntry(card, textvariable=name_var, justify="center", font=("Arial", 12),
                                 fg_color="transparent", border_width=0, text_color="#AAAAAA", width=140)
            entry.pack(side="bottom", padx=10, pady=(0, 10))
            entry.bind("<Return>", lambda e, old=name: self.rename_person(old, name_var.get()))

    # ================================================================
    # TAB & NAVIGATION
    # ================================================================
    def _update_tab_styles(self):
        active = {"fg_color": "#1F6AA5", "hover_color": "#1A5A8A", "text_color": "#FFFFFF"}
        inactive = {"fg_color": "#2B2B2B", "hover_color": "#3A3A3A", "text_color": "#999999"}
        self.images_tab_btn.configure(**(active if self.current_tab == "images" else inactive))
        self.faces_tab_btn.configure(**(active if self.current_tab == "faces" else inactive))

    def _show_tab_header(self):
        self.header_lbl.pack_forget()
        self.back_btn.pack_forget()
        self.tab_frame.pack(side="left", fill="x", expand=True)
        self._update_tab_styles()

    def _show_detail_header(self, title):
        self.tab_frame.pack_forget()
        self.header_lbl.configure(text=title)
        self.header_lbl.pack(side="left", fill="x", expand=True)
        self.back_btn.pack(side="right", padx=0)

    def show_images_tab(self):
        self.current_page = "images"
        self.current_tab = "images"
        self.current_person_view = None
        self._show_tab_header()
        self.gallery_frame.pack_forget()
        self.sort_bar.pack(fill="x", pady=(6, 2))
        self.gallery_frame.pack(fill="both", expand=True)
        self.reload_gallery()

    def show_faces_tab(self):
        self.current_page = "faces"
        self.current_tab = "faces"
        self.current_person_view = None
        self._show_tab_header()
        self.sort_bar.pack_forget()
        self.gallery_frame.pack_forget()
        self.gallery_frame.pack(fill="both", expand=True)
        self.reload_gallery()

    def show_person_detail(self, name):
        self.current_page = "detail"
        self.current_person_view = name
        self.sort_bar.pack_forget()
        self.gallery_frame.pack_forget()
        self._show_detail_header(f"{name}'s Photos")
        self.gallery_frame.pack(fill="both", expand=True)
        self.reload_gallery()

    def _go_back(self):
        if self.current_tab == "faces":
            self.show_faces_tab()
        else:
            self.show_images_tab()

    def _on_sort_changed(self, choice):
        sort_map = {
            "Name (A-Z)": "name_asc", "Name (Z-A)": "name_desc",
            "Date (Newest)": "date_desc", "Date (Oldest)": "date_asc",
            "Size (Largest)": "size_desc", "Size (Smallest)": "size_asc",
        }
        self._sort_by = sort_map.get(choice, "name_asc")
        self.reload_gallery()

    def _on_search_changed(self, *args):
        self._search_query = self.search_entry.get().strip().lower()
        if self.resize_timer is not None:
            self.after_cancel(self.resize_timer)
        self.resize_timer = self.after(200, self.reload_gallery)

    def check_resize(self, event):
        physical_width = self.main_area.winfo_width()
        try:
            scaling = ctk.ScalingTracker.get_widget_scaling(self)
        except Exception:
            scaling = 1.0

        logical_width = physical_width / scaling
        new_cols = max(1, int((logical_width - 35) // 186))

        if new_cols != self.current_cols:
            self.current_cols = new_cols
            if self.resize_timer is not None:
                self.after_cancel(self.resize_timer)
            self.resize_timer = self.after(150, self.reload_gallery)

    # ================================================================
    # GALLERY
    # ================================================================
    def reload_gallery(self):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
        for i in range(20):
            self.gallery_frame.grid_columnconfigure(i, weight=0)

        conn = get_connection()
        c = conn.cursor()

        if self.current_page == "images":
            c.execute("SELECT filepath FROM photos")
            images = [row[0] for row in c.fetchall()]
            if self._search_query:
                images = [p for p in images if self._search_query in os.path.basename(p).lower()]
            images = self._sort_images(images)
            self._detail_image_list = images
            self.image_count_lbl.configure(text=f"{len(images)} images")
            self.render_grid(images, is_people=False)

        elif self.current_page == "faces":
            c.execute("SELECT name FROM people")
            people = [{"name": row[0]} for row in c.fetchall()]
            if self._search_query:
                people = [p for p in people if self._search_query in p["name"].lower()]
            self.render_grid(people, is_people=True)

        elif self.current_page == "detail":
            c.execute("""
                SELECT photos.filepath FROM photos
                JOIN photo_faces ON photos.id = photo_faces.photo_id
                JOIN people ON people.id = photo_faces.person_id
                WHERE people.name = ?
            """, (self.current_person_view,))
            images = [row[0] for row in c.fetchall()]
            if self._search_query:
                images = [p for p in images if self._search_query in os.path.basename(p).lower()]
            images = self._sort_images(images)
            self._detail_image_list = images
            self.render_grid(images, is_people=False)

        conn.close()

    def _sort_images(self, image_paths):
        """Sort image file paths based on the current sort selection."""
        try:
            if self._sort_by == "name_asc":
                return sorted(image_paths, key=lambda p: os.path.basename(p).lower())
            elif self._sort_by == "name_desc":
                return sorted(image_paths, key=lambda p: os.path.basename(p).lower(), reverse=True)
            elif self._sort_by == "date_desc":
                return sorted(image_paths, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
            elif self._sort_by == "date_asc":
                return sorted(image_paths, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
            elif self._sort_by == "size_desc":
                return sorted(image_paths, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)
            elif self._sort_by == "size_asc":
                return sorted(image_paths, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0)
        except Exception:
            pass
        return image_paths

    def render_grid(self, items, is_people):
        if not items:
            ctk.CTkLabel(self.gallery_frame, text="No items found.").pack(pady=20)
            return

        for i in range(self.current_cols):
            self.gallery_frame.grid_columnconfigure(i, weight=1)

        row, col = 0, 0
        for idx, item in enumerate(items):
            if is_people:
                name = item["name"]
                thumb_path = os.path.join(THUMBS_DIR, f"{name}.jpg")
                img_path = thumb_path if os.path.exists(thumb_path) else None
                self._create_card(row, col, img_path, name=name, is_person_card=True)
            else:
                self._create_card(row, col, item, is_person_card=False, img_index=idx)

            col += 1
            if col >= self.current_cols:
                col = 0
                row += 1

    # ================================================================
    # DATA OPERATIONS
    # ================================================================
    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            self.status_label.configure(text="Processing...", text_color="#FFA500")
            self.update()
            try:
                process_single_image(file_path)
                self._image_cache.clear()
                self.reload_gallery()
                self.status_label.configure(text="Success!", text_color="#00FF00")
            except Exception as e:
                print(e)
                self.status_label.configure(text="Error", text_color="#FF0000")
                messagebox.showerror("Error", str(e))

    def start_scan(self):
        if self.is_scanning:
            return
        directory = filedialog.askdirectory(title="Select Folder to Scan")
        if not directory:
            return

        self.is_scanning = True
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="Preparing scan...", text_color="white")
        threading.Thread(target=self._scan_thread, args=(directory,), daemon=True).start()

    def _scan_thread(self, root_dir):
        image_files = []
        self.after(0, lambda: self.status_label.configure(text="Searching for files..."))
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_files.append(os.path.join(root, file))

        total = len(image_files)
        if total == 0:
            self.after(0, lambda: self._scan_finished("No images found."))
            return

        known_ids, known_names, known_encodings = load_known_encodings()

        for count, img_path in enumerate(image_files, 1):
            self.after(0, lambda c=count, t=total: self.status_label.configure(text=f"Processing {c}/{t}..."))
            try:
                process_with_cache(img_path, known_ids, known_names, known_encodings)
            except Exception as e:
                print(f"Skipped {img_path}: {e}")

        self.after(0, lambda: self._scan_finished("Scan Complete!"))

    def _scan_finished(self, status_text):
        self.is_scanning = False
        self.scan_btn.configure(state="normal", text="\ud83d\udd0d Scan Storage")
        self.status_label.configure(text=status_text, text_color="#00FF00")
        self._image_cache.clear()
        self.reload_gallery()

    def rename_person(self, old_name, new_name):
        new_name = new_name.strip()
        if not new_name or old_name == new_name:
            return

        conn = get_connection()
        c = conn.cursor()

        c.execute("SELECT id FROM people WHERE name = ?", (new_name,))
        if c.fetchone():
            messagebox.showerror("Error", "That name already exists!")
            conn.close()
            return

        c.execute("UPDATE people SET name = ? WHERE name = ?", (new_name, old_name))
        conn.commit()
        conn.close()

        old_thumb = os.path.join(THUMBS_DIR, f"{old_name}.jpg")
        new_thumb = os.path.join(THUMBS_DIR, f"{new_name}.jpg")
        if os.path.exists(old_thumb):
            os.rename(old_thumb, new_thumb)

        self._image_cache = {k: v for k, v in self._image_cache.items() if old_thumb not in k[0]}
        self.reload_gallery()
        self.focus()

    # ================================================================
    # IMAGE VIEWER
    # ================================================================
    def _open_image_viewer(self, index):
        if not self._detail_image_list:
            return
        if self._viewer_overlay:
            try:
                self._viewer_overlay.close_viewer()
            except Exception:
                pass

        self._viewer_overlay = ImageViewerOverlay(self.main_area, self, self._detail_image_list, index)
