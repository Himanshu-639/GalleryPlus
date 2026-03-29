"""Gallery+ — Entry point."""

from app.config import *          # noqa: F401,F403 — initialises theme & directories
from app.database import init_db
from app.face_app import FaceApp


def main():
    init_db()
    app = FaceApp()
    app.mainloop()


if __name__ == "__main__":
    main()