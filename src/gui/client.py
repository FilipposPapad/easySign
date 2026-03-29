import sys
import tkinter as tk

from app import SignApp

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    path_arg = sys.argv[1]
    root = tk.Tk()
    app = SignApp(root, path_arg)
    root.mainloop()
