import sys
import tkinter as tk
from video_player import VideoPlayer

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayer(root)
    
    # Configurar o comportamento de fechamento
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    root.mainloop()