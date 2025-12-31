import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import cv2
import pickle
import face_recognition

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
        with open(DB_FILE, "rb") as f:
            known_people_db = pickle.load(f)
            print(f"Loaded {len(known_people_db)} people.")

def save_db():
    with open(DB_FILE, "wb") as f:
        pickle.dump(known_people_db, f)

def get_person_folder(name):
    return os.path.join(KNOWN_FACES_DIR, name)


class FaceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FaceReco AI")
        self.geometry("1100x700")

        load_db()

        # Grid Configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # STATE FOR DYNAMIC GRID
        self.current_cols = 1

        # 1. LEFT SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="FaceReco", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.upload_btn = ctk.CTkButton(self.sidebar, text="+ Upload Image", height=40,
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      fg_color="#1F6AA5", hover_color="#144870",
                                      command=self.upload_image)
        self.upload_btn.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.status_label = ctk.CTkLabel(self.sidebar, text="System Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar.grid_rowconfigure(3, weight=1)
        self.credit_label = ctk.CTkLabel(self.sidebar, text="v1.4 Stable Scroll", text_color="#555")
        self.credit_label.grid(row=4, column=0, pady=20)

        # 2. MAIN CONTENT AREA
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.header_lbl = ctk.CTkLabel(self.main_area, text="People Gallery", 
                                     font=ctk.CTkFont(family="Arial", size=28, weight="bold"),
                                     anchor="w")
        self.header_lbl.pack(fill="x", pady=(10, 15), padx=10)

        # Scrollable Gallery
        self.gallery_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.gallery_frame.pack(fill="both", expand=True)

        # --- FIX: Bind Resize to PARENT (main_area), NOT the scrollable frame ---
        self.main_area.bind("<Configure>", self.check_resize)
        
        # Initial Render
        self.reload_gallery()

    def check_resize(self, event):
        """
        Dynamically calculates columns based on width.
        """
        # We check the width of main_area, but we must account for the sidebar
        # taking up space if the event returns full window width. 
        # However, since we bound to main_area, event.width IS the gallery width.
        
        available_width = event.width - 60 # Subtract padding/scrollbar safety buffer
        
        # Card width (170) + X-Padding (16) = 186px
        item_total_width = 186
        
        new_cols = available_width // item_total_width
        
        if new_cols < 1: new_cols = 1
        
        if new_cols != self.current_cols:
            self.current_cols = int(new_cols)
            self.reload_gallery()

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            self.status_label.configure(text="Processing...", text_color="#FFA500") 
            self.update() 
            
            try:
                self.process_engine(file_path)
                self.reload_gallery()
                self.status_label.configure(text="Success!", text_color="#00FF00") 
            except Exception as e:
                print(e)
                self.status_label.configure(text="Error", text_color="#FF0000")
                messagebox.showerror("Error", str(e))

    def process_engine(self, image_path):
        image_rgb = face_recognition.load_image_file(image_path)
        image_bgr = cv2.imread(image_path)
        
        face_locations = face_recognition.face_locations(image_rgb)
        face_encodings = face_recognition.face_encodings(image_rgb, face_locations)

        if not face_locations:
            messagebox.showwarning("No Face", "No faces found.")
            return

        for face_encoding, face_location in zip(face_encodings, face_locations):
            name = "Unknown"
            matches = []

            if len(known_people_db) > 0:
                known_embeddings = [p['encoding'] for p in known_people_db]
                matches = face_recognition.compare_faces(known_embeddings, face_encoding, tolerance=0.6)
            
            if True in matches:
                idx = matches.index(True)
                name = known_people_db[idx]['name']
            else:
                new_id = len(known_people_db) + 1
                name = f"Person_{new_id}"
                known_people_db.append({'name': name, 'encoding': face_encoding})
                save_db()
                os.makedirs(get_person_folder(name), exist_ok=True)

            save_path = os.path.join(get_person_folder(name), os.path.basename(image_path))
            cv2.imwrite(save_path, image_bgr)

    def reload_gallery(self):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        row = 0
        col = 0
        
        for person in known_people_db:
            self.create_person_card(person['name'], row, col)
            
            col += 1
            if col >= self.current_cols:
                col = 0
                row += 1

    def create_person_card(self, name, r, c):
        # 1. Card Container
        card_width = 170
        card_height = 200
        
        card = ctk.CTkFrame(self.gallery_frame, width=card_width, height=card_height, 
                            corner_radius=0, fg_color="#2B2B2B")
        card.grid(row=r, column=c, padx=8, pady=8)
        card.grid_propagate(False)

        # 2. Thumbnail
        folder = get_person_folder(name)
        images = os.listdir(folder)
        display_image = None
        
        if images:
            img_path = os.path.join(folder, images[0])
            try:
                pil_img = Image.open(img_path)
                pil_img = pil_img.resize((150, 150), Image.Resampling.LANCZOS)
                display_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 150))
            except:
                pass

        if display_image:
            img_label = ctk.CTkLabel(card, image=display_image, text="")
            img_label.pack(pady=(10, 0))
        else:
            ctk.CTkLabel(card, text="No Image", height=140).pack(pady=(10,0))

        # 3. Rename Field
        name_var = ctk.StringVar(value=name)
        entry = ctk.CTkEntry(
            card, 
            textvariable=name_var, 
            justify="right",           
            font=("Arial", 11),
            fg_color="transparent",    
            border_width=0,            
            text_color="#AAAAAA",      
            width=140
        )
        entry.pack(side="bottom", anchor="e", padx=10, pady=(0, 10))
        entry.bind("<Return>", lambda event: self.rename_person(name, name_var.get()))

    def rename_person(self, old_name, new_name):
        if old_name == new_name: return

        try:
            old_path = get_person_folder(old_name)
            new_path = get_person_folder(new_name)
            os.rename(old_path, new_path)
            
            for p in known_people_db:
                if p['name'] == old_name:
                    p['name'] = new_name
                    break
            
            save_db()
            self.reload_gallery()
            print(f"Renamed {old_name} -> {new_name}")
            self.focus() 
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not rename: {e}")

if __name__ == "__main__":
    app = FaceApp()
    app.mainloop()