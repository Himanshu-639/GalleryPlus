# 📸 Smart Face Sorter (Incremental Clustering)

A Python-based application that automatically organizes a collection of photos by grouping them based on faces. Unlike traditional clustering that requires all data at once, this app uses **Incremental Clustering** to learn and group faces one by one as they are uploaded.

## 🚀 Key Features

* **Incremental Learning:** You don't need a dataset to start. The app starts empty and learns new faces as you add images.
* **Automatic Grouping:** If a face matches an existing person, it adds it to their group. If it's a new face, it automatically creates a new "Person X" group.
* **Persistent Memory:** Uses `pickle` to save face encodings, so the app remembers who is who even after you restart the computer.
* **Folder Organization:** Automatically creates folders for each person and sorts images into them.
* **Privacy-First:** All processing happens locally on your machine.

## 🛠️ Tech Stack

* **Python 3.x**
* **face_recognition** (State-of-the-art face recognition built on dlib)
* **OpenCV** (Image processing and saving)
* **Pickle** (Data serialization for memory)

## 🧠 How It Works

1.  **Face Detection:** The app scans an image and locates all faces.
2.  **Encoding:** It converts each face into a 128-dimensional vector (a unique mathematical fingerprint).
3.  **Matching:**
    * It compares the new face against the database of known faces.
    * If the distance is low (tolerance < 0.6), it's a match!
    * If the distance is high, it treats it as a **New Person**.
4.  **Storage:** The image is saved into the corresponding folder (e.g., `known_faces/Person_1/`).

## 📦 Installation

1.  Clone the repo:
    ```bash
    git clone [https://github.com/your-username/smart-face-sorter.git](https://github.com/your-username/smart-face-sorter.git)
    cd smart-face-sorter
    ```

2.  Install dependencies:
    ```bash
    pip install face_recognition opencv-python
    ```
    *(Note: You may need CMake and Visual Studio Build Tools C++ installed for dlib)*

3.  Run the engine:
    ```bash
    python main.py
    ```

## 🔮 Roadmap

* [x] Core Logic (Detection & Grouping)
* [x] Persistent Storage (Save/Load Memory)
* [ ] GUI Implementation (Tkinter/PyQt) for easy drag-and-drop
* [ ] Name Editing (Rename "Person_1" to "John")

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.