import os
import cv2
import pickle
import face_recognition

KNOWN_FACES_DIR = "known_faces"
DB_FILE = "encodings.pickle"

known_people_db = []

def load_existing_db():
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)
    
    global known_people_db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            known_people_db = pickle.load(f)
        print(f"History of {len(known_people_db)} people loaded.")

def save_db():
    with open("encodings.pickle", "wb") as f:
        pickle.dump(known_people_db, f)

def process_new_image(image_path):
    img = face_recognition.load_image_file(image_path)
    img_to_save = cv2.imread(image_path)
    face_locations = face_recognition.face_locations(img)
    face_encodings = face_recognition.face_encodings(img, face_locations)

    print(f"{len(face_encodings)} face(s) in {image_path}")

    for face_encoding, face_location in zip(face_encodings, face_locations):
        name="unknown"
        matches = []

        if len(known_people_db) > 0:
            known_embeddings = [person['encoding'] for person in known_people_db]
            matches = face_recognition.compare_faces(known_embeddings, face_encoding, tolerance=0.6)
        
        if True in matches:
            first_match_index = matches.index(True)
            name = known_people_db[first_match_index]['name']
            print(f"Math Found. it is {name}")
        else:
            new_id = len(known_people_db) + 1
            name = f"Person_{new_id}"

            known_people_db.append({'name': name, 'encoding':face_encoding})
            save_db()
            print(f"Face not found. Created new group {name}")

            os.makedirs(f"{KNOWN_FACES_DIR}/{name}", exist_ok=True)

        save_path = f"{KNOWN_FACES_DIR}/{name}/{os.path.basename(image_path)}"
        cv2.imwrite(save_path, img_to_save)

if __name__ == "__main__":
    load_existing_db()
    while True:
        path = input("\nEnter image path (or 'q' to quit): ").strip().strip('"')
        if path.lower() == 'q':
            break
        if os.path.exists(path):
            process_new_image(path)
        else:
            print("File not found! Try again.")