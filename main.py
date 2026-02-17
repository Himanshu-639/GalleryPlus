import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import cv2
import pickle
import face_recognition
import threading  # <--- NEW: For background scanning

# --- THEME CONFIG ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

KNOWN_FACES_DIR = "known_faces"
DB_FILE = "encodings.pickle"
known_people_db = []

# --- BACKEND LOGIC ---
def load_db():
    global known_people_db
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                known_people_db = pickle.load(f)
        except EOFError:
            known_people_db = []

def save_db():
    with open(DB_FILE, "wb") as f:
        pickle.dump(known_people_db, f)

def get_person_folder(name):
    return os.path.join(KNOWN_FACES_DIR, name)

class FaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FaceReco - Desktop Project")
        self.geometry("1100x700")
        load_db()

        # State
        self.current_page = "home" 
        self.current_person_view = None
        self.current_cols = 1
        self.is_scanning = False # <--- NEW: To prevent double scanning

        # Layout Config
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. UI SETUP
        self._setup_sidebar()
        self._setup_main_area()
        
        self.show_home()

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="FaceReco", font=("Arial", 24, "bold")).grid(row=0, column=0, padx=20, pady=(30, 20))
        
        # Original Upload Button
        ctk.CTkButton(self.sidebar, text="+ Upload Image", height=40, font=("Arial", 14, "bold"),
                      fg_color="#1F6AA5", hover_color="#144870",
                      command=self.upload_image).grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # NEW: Scan Button
        self.scan_btn = ctk.CTkButton(self.sidebar, text="🔍 Scan Storage", height=40, font=("Arial", 14, "bold"),
                      fg_color="#2B8C58", hover_color="#1E613D",
                      command=self.start_scan)
        self.scan_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(self.sidebar, text="System Ready", text_color="gray", wraplength=200)
        self.status_label.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar.grid_rowconfigure(4, weight=1) # Spacer
        ctk.CTkLabel(self.sidebar, text="v1.1 FaceReco", text_color="#555").grid(row=5, column=0, pady=20)

    def _setup_main_area(self):
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))
        
        # Header
        self.header_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(10, 15), padx=(10, 20))

        self.header_lbl = ctk.CTkLabel(self.header_frame, text="People Gallery", font=("Arial", 28, "bold"), anchor="w")
        self.header_lbl.pack(side="left", fill="x", expand=True)

        self.back_btn = ctk.CTkButton(self.header_frame, text="← Back", width=80, fg_color="transparent", 
                                      border_width=1, text_color="#DDD", hover_color="#333",
                                      command=self.show_home)
        
        # Gallery
        self.gallery_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent", corner_radius=0)
        self.gallery_frame.pack(fill="both", expand=True)
        self.main_area.bind("<Configure>", self.check_resize)

    # --- HELPERS ---
    def _load_image(self, path, size=(150, 150)):
        try:
            pil_img = Image.open(path)
            pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        except:
            return None

    def _create_card(self, row, col, img_path, name=None, is_person_card=False):
        card = ctk.CTkFrame(self.gallery_frame, width=170, height=200 if is_person_card else 170, 
                            corner_radius=0, fg_color="#2B2B2B")
        card.grid(row=row, column=col, padx=8, pady=8)
        card.grid_propagate(False)

        display_image = self._load_image(img_path) if img_path else None
        
        if display_image:
            lbl = ctk.CTkLabel(card, image=display_image, text="", cursor="hand2" if is_person_card else "")
            lbl.pack(pady=(10, 0) if is_person_card else 0, expand=True)
            if is_person_card:
                lbl.bind("<Button-1>", lambda e: self.show_person_detail(name))
        else:
            ctk.CTkLabel(card, text="No Image" if is_person_card else "Error").pack(pady=(10,0) if is_person_card else 0, expand=True)

        if is_person_card:
            name_var = ctk.StringVar(value=name)
            entry = ctk.CTkEntry(card, textvariable=name_var, justify="right", font=("Arial", 11),
                                 fg_color="transparent", border_width=0, text_color="#AAAAAA", width=140)
            entry.pack(side="bottom", anchor="e", padx=10, pady=(0, 10))
            entry.bind("<Return>", lambda e: self.rename_person(name, name_var.get()))

    # --- NAVIGATION ---
    def show_home(self):
        self.current_page = "home"
        self.current_person_view = None
        self.back_btn.pack_forget()
        self.header_lbl.configure(text="People Gallery")
        self.reload_gallery()

    def show_person_detail(self, name):
        self.current_page = "detail"
        self.current_person_view = name
        self.back_btn.pack(side="right", padx=0)
        self.header_lbl.configure(text=f"{name}'s Photos")
        self.reload_gallery()

    # --- CORE LOGIC ---
    def check_resize(self, event):
        new_cols = max(1, (event.width - 40) // 186)
        if new_cols != self.current_cols:
            self.current_cols = int(new_cols)
            self.reload_gallery()

    def reload_gallery(self):
        # Clear existing widgets
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        if self.current_page == "home":
            # Pass only names/people
            self.render_grid(known_people_db, is_people=True)
        elif self.current_page == "detail":
            folder = get_person_folder(self.current_person_view)
            if os.path.exists(folder):
                images = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                self.render_grid(images, is_people=False)
            else:
                ctk.CTkLabel(self.gallery_frame, text="Folder not found!").pack()

    def render_grid(self, items, is_people):
        if not items:
            ctk.CTkLabel(self.gallery_frame, text="No items found.").pack()
            return

        row, col = 0, 0
        for item in items:
            # Handle cases where items might be people dicts or image paths
            if is_people:
                name = item['name']
                folder = get_person_folder(name)
                files = os.listdir(folder) if os.path.exists(folder) else []
                img_path = os.path.join(folder, files[0]) if files else None
                self._create_card(row, col, img_path, name=name, is_person_card=True)
            else:
                self._create_card(row, col, item, is_person_card=False)

            col += 1
            if col >= self.current_cols:
                col = 0
                row += 1

    # --- DATA OPERATIONS & SCANNING ---
    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            self.status_label.configure(text="Processing...", text_color="#FFA500") 
            self.update() 
            try:
                # Force Save for single upload
                self.process_engine(file_path, save_immediate=True) 
                self.reload_gallery()
                self.status_label.configure(text="Success!", text_color="#00FF00") 
            except Exception as e:
                print(e)
                self.status_label.configure(text="Error", text_color="#FF0000")
                messagebox.showerror("Error", str(e))

    def start_scan(self):
        """UI Trigger for scanning storage"""
        if self.is_scanning:
            messagebox.showinfo("Info", "Scan already in progress.")
            return

        # Let user pick root directory (e.g., C:/ or Users/Pictures)
        directory = filedialog.askdirectory(title="Select Folder to Scan (e.g., D: or Pictures)")
        if not directory:
            return

        self.is_scanning = True
        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="Preparing scan...", text_color="white")
        
        # Start Thread
        threading.Thread(target=self._scan_thread, args=(directory,), daemon=True).start()

    def _scan_thread(self, root_dir):
        """Background thread logic"""
        image_files = []
        
        # 1. Gather all files first
        self.status_label.configure(text="Searching for files...")
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(root, file))

        total = len(image_files)
        if total == 0:
            self._scan_finished("No images found.")
            return

        # 2. Process Loop
        count = 0
        for img_path in image_files:
            count += 1
            # Update status safely from thread
            self.status_label.configure(text=f"Processing {count}/{total}...")
            try:
                # Pass False to save_immediate so we don't write DB 1000 times
                self.process_engine(img_path, save_immediate=False)
            except Exception as e:
                print(f"Skipped {img_path}: {e}")
        
        # 3. Final Save
        save_db()
        self._scan_finished("Scan Complete!")

    def _scan_finished(self, status_text):
        """Called when thread finishes to reset UI"""
        self.is_scanning = False
        self.scan_btn.configure(state="normal", text="🔍 Scan Storage")
        self.status_label.configure(text=status_text, text_color="#00FF00")
        # Refresh UI on main thread
        self.after(0, self.reload_gallery)

    def process_engine(self, image_path, save_immediate=True):
        """
        The core face recognition logic.
        save_immediate: Set to False during batch scans to improve speed.
        """
        # Load logic
        image_rgb = face_recognition.load_image_file(image_path)
        image_bgr = cv2.imread(image_path)
        
        # Optimization: Upsample only for small images if needed, or keep 1 (default)
        face_locations = face_recognition.face_locations(image_rgb)
        face_encodings = face_recognition.face_encodings(image_rgb, face_locations)

        if not face_locations:
            return # Skip silently in batch mode

        for face_encoding, face_location in zip(face_encodings, face_locations):
            name = "Unknown"
            matches = []
            
            # 1. Compare with existing DB
            if len(known_people_db) > 0:
                known_embeddings = [p['encoding'] for p in known_people_db]
                matches = face_recognition.compare_faces(known_embeddings, face_encoding, tolerance=0.5) 
                # Reduced tolerance slightly for stricter matching
            
            # 2. Match or New
            if True in matches:
                idx = matches.index(True)
                name = known_people_db[idx]['name']
            else:
                new_id = len(known_people_db) + 1
                name = f"Person_{new_id}"
                # Append to memory
                known_people_db.append({'name': name, 'encoding': face_encoding})
                
                # Only write to disk if requested (Single upload mode)
                if save_immediate:
                    save_db()
                
                os.makedirs(get_person_folder(name), exist_ok=True)

            # 3. Save the cropped/found face image to the person's folder
            save_path = os.path.join(get_person_folder(name), f"{name}_{os.path.basename(image_path)}")
            # Ensure unique filename to prevent overwrites in batch
            if os.path.exists(save_path):
                import uuid
                save_path = os.path.join(get_person_folder(name), f"{uuid.uuid4().hex[:8]}_{os.path.basename(image_path)}")
                
            cv2.imwrite(save_path, image_bgr)

    def rename_person(self, old_name, new_name):
        if old_name == new_name: return
        try:
            old_path = get_person_folder(old_name)
            new_path = get_person_folder(new_name)
            
            if os.path.exists(new_path):
                messagebox.showerror("Error", "Name already exists!")
                return

            os.rename(old_path, new_path)
            
            for p in known_people_db:
                if p['name'] == old_name:
                    p['name'] = new_name
                    break
            
            save_db()
            self.reload_gallery()
            self.focus()
        except Exception as e:
            messagebox.showerror("Error", f"Could not rename: {e}")

if __name__ == "__main__":
    app = FaceApp()
    app.mainloop()