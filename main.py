import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
import os
import cv2
import pickle
import face_recognition

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

KNOWN_FACES_DIR = "known_faces"
DB_FILE = "encodings.pickle"
known_people_db = []

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

        self.title("FaceReco")
        self.geometry("1000x700")

        load_db()

        # LAYOUT: Grid Configuration (2 Columns)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. LEFT SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="FaceReco", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.upload_btn = ctk.CTkButton(self.sidebar, text="+ Upload Image", command=self.upload_image)
        self.upload_btn.grid(row=1, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="Ready", text_color="gray")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

        # 2. MAIN GALLERY (Right Side)
        self.gallery_frame = ctk.CTkScrollableFrame(self, label_text="People Gallery")
        self.gallery_frame.grid(row=0, column=1, padx=(5, 0), pady=10, sticky="nsew")

        # Initial Render
        self.reload_gallery()

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if file_path:
            self.status_label.configure(text="Processing...", text_color="orange")
            self.update() # Force UI update
            
            try:
                self.process_engine(file_path)
                self.reload_gallery()
                self.status_label.configure(text="Done!", text_color="green")
            except Exception as e:
                print(e)
                self.status_label.configure(text="Error!", text_color="red")
                messagebox.showerror("Error", str(e))

    def process_engine(self, image_path):
        # 1. Load Images
        image_rgb = face_recognition.load_image_file(image_path)
        image_bgr = cv2.imread(image_path)
        
        # 2. Detect
        face_locations = face_recognition.face_locations(image_rgb)
        face_encodings = face_recognition.face_encodings(image_rgb, face_locations)

        if not face_locations:
            messagebox.showwarning("No Face", "No faces found in this image.")
            return

        for face_encoding, face_location in zip(face_encodings, face_locations):
            name = "Unknown"
            matches = []

            # 3. Compare
            if len(known_people_db) > 0:
                known_embeddings = [p['encoding'] for p in known_people_db]
                matches = face_recognition.compare_faces(known_embeddings, face_encoding, tolerance=0.6)
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_people_db[first_match_index]['name']
            else:
                # New Person
                new_id = len(known_people_db) + 1
                name = f"Person_{new_id}"
                known_people_db.append({'name': name, 'encoding': face_encoding})
                save_db()
                os.makedirs(get_person_folder(name), exist_ok=True)

            # 4. Save Image
            save_path = os.path.join(get_person_folder(name), os.path.basename(image_path))
            cv2.imwrite(save_path, image_bgr)

    def reload_gallery(self):
        # Clear existing widgets in the scrollable frame
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Grid Logic for Cards
        row = 0
        col = 0
        MAX_COLS = 6

        for person in known_people_db:
            name = person['name']
            self.create_person_card(name, row, col)
            
            col += 1
            if col >= MAX_COLS:
                col = 0
                row += 1

    def create_person_card(self, name, r, c):
        # 1. Card Container
        card = ctk.CTkFrame(self.gallery_frame)
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")

        # 2. Load Thumbnail
        folder = get_person_folder(name)
        images = os.listdir(folder)
        if images:
            img_path = os.path.join(folder, images[0])
            pil_img = Image.open(img_path)
            
            # CustomTkinter Image Object (High DPI friendly)
            my_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(150, 150))
            
            img_label = ctk.CTkLabel(card, image=my_image, text="")
            img_label.pack(pady=10, padx=10)
        else:
            ctk.CTkLabel(card, text="No Image", width=150, height=150).pack()

        # 3. Rename Field
        # We use a StringVar to track the text
        name_var = ctk.StringVar(value=name)
        entry = ctk.CTkEntry(card, textvariable=name_var, justify="center")
        entry.pack(pady=5, padx=5)

        # 4. Save Button (Small)
        btn = ctk.CTkButton(card, text="Save Name", height=25, 
                            command=lambda: self.rename_person(name, name_var.get()))
        btn.pack(pady=(0, 10))

    def rename_person(self, old_name, new_name):
        if old_name == new_name: return

        try:
            old_path = get_person_folder(old_name)
            new_path = get_person_folder(new_name)
            
            os.rename(old_path, new_path)
            
            # Update RAM Database
            for p in known_people_db:
                if p['name'] == old_name:
                    p['name'] = new_name
                    break
            
            save_db()
            self.reload_gallery() # Refresh UI
            print(f"Renamed {old_name} -> {new_name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not rename: {e}")

if __name__ == "__main__":
    app = FaceApp()
    app.mainloop()