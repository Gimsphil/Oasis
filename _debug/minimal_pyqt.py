import sys
from PyQt6.QtWidgets import QApplication, QLabel

import ctypes
try:
    ctypes.windll.user32.MessageBoxW(0, "Python Started", "Debug", 0)
except:
    pass

app = QApplication(sys.argv)
label = QLabel("Minimal PyQt Test Success!", None)
label.resize(400, 200)
label.show()
print("PyQt Window Shown")
sys.exit(app.exec())
