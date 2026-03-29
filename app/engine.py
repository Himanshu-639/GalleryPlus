"""Face recognition processing engine."""

import os
import pickle
import cv2
import numpy as np
import face_recognition

from app.config import THUMBS_DIR
from app.database import get_connection


def process_single_image(image_path):
    """Process a single image. Loads known encodings from DB each time (used for single uploads)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, encoding FROM people")
    known_people = c.fetchall()
    conn.close()

    known_ids = [p[0] for p in known_people]
    known_names = [p[1] for p in known_people]
    known_encodings = [pickle.loads(p[2]) for p in known_people]

    process_with_cache(image_path, known_ids, known_names, known_encodings)


def load_known_encodings():
    """Load all known face encodings from the database. Returns (ids, names, encodings) lists."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, encoding FROM people")
    known_people = c.fetchall()
    conn.close()

    known_ids = [p[0] for p in known_people]
    known_names = [p[1] for p in known_people]
    known_encodings = [pickle.loads(p[2]) for p in known_people]
    return known_ids, known_names, known_encodings


def process_with_cache(image_path, known_ids, known_names, known_encodings):
    """Core processing engine that works with a pre-loaded encoding cache."""
    image_rgb = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image_rgb)
    face_encodings = face_recognition.face_encodings(image_rgb, face_locations)

    if not face_locations:
        return

    conn = get_connection()
    c = conn.cursor()

    # Add this photo to the database
    c.execute("INSERT OR IGNORE INTO photos (filepath) VALUES (?)", (image_path,))
    c.execute("SELECT id FROM photos WHERE filepath = ?", (image_path,))
    photo_id = c.fetchone()[0]

    # Process each face found in the image
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        person_id = None

        if known_encodings:
            # Use face_distance for better matching when multiple faces match
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_idx = np.argmin(distances)
            if distances[best_idx] <= 0.5:
                person_id = known_ids[best_idx]

        if person_id is None:
            # New person found
            c.execute("SELECT COUNT(id) FROM people")
            count = c.fetchone()[0]
            name = f"Person_{count + 1}"

            encoding_blob = pickle.dumps(face_encoding)
            c.execute("INSERT INTO people (name, encoding) VALUES (?, ?)", (name, encoding_blob))
            person_id = c.lastrowid

            # Update in-memory cache for the next face in the loop
            known_encodings.append(face_encoding)
            known_ids.append(person_id)
            known_names.append(name)

            # Crop and save thumbnail
            face_image = image_rgb[top:bottom, left:right]
            face_image_bgr = cv2.cvtColor(face_image, cv2.COLOR_RGB2BGR)
            thumb_path = os.path.join(THUMBS_DIR, f"{name}.jpg")
            cv2.imwrite(thumb_path, face_image_bgr)

        # Link person to photo
        c.execute("INSERT OR IGNORE INTO photo_faces (person_id, photo_id) VALUES (?, ?)", (person_id, photo_id))

    conn.commit()
    conn.close()
