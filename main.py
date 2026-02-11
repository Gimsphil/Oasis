import sys
import os
import ctypes
import traceback
import subprocess
import time
import datetime

# Fix encoding for Windows console output
if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Redirect stdout/stderr to file for debugging
class DebugOutput:
    def __init__(self):
        self.file = open("app_debug_output.txt", "w", encoding="utf-8")
        self.terminal = sys.stdout
    
    def write(self, msg):
        self.file.write(msg)
        self.file.flush()
        self.terminal.write(msg)
    
    def flush(self):
        self.file.flush()
        self.terminal.flush()

# Uncomment this line to enable debug output to file
# sys.stdout = DebugOutput()

# [DEBUG] Critical File Logging
def log_to_file(msg):
    try:
        with open("startup_debug.log", "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

log_to_file("=== Application Starting ===")
log_to_file(f"Python executable: {sys.executable}")
log_to_file(f"Current working directory: {os.getcwd()}")
log_to_file(f"sys.path: {sys.path}")


# Windows 콘솔 숨기기 (GUI만 표시)
# try:
#     import ctypes
#     hwnd = ctypes.windll.kernel32.GetConsoleWindow()
#     ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE (콘솔 숨기기)
# except:
#     pass

# 1. 시각적 디버깅용 메시지 박스 함수
def msgbox(title, text, style=0):
    """
    Windows Native Message Box를 띄웁니다.
    """
    try:
        return ctypes.windll.user32.MessageBoxW(0, text, title, style)
    except Exception as e:
        print(f"[ERROR] Failed to show MessageBox: {e}")
        return 0

# 2. 경로 설정 (중복 제거 및 명확화)
# 현재 디렉토리와 하위 주요 폴더들을 sys.path에 추가하여 모듈 임포트 오류 방지
current_dir = os.path.dirname(os.path.abspath(__file__))
module_paths = [
    current_dir,
    os.path.join(current_dir, "core"),
    os.path.join(current_dir, "utils"),
    os.path.join(current_dir, "ui"),
    os.path.join(current_dir, "managers"),
    os.path.join(current_dir, "popups")
]

for path in module_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"[DEBUG] sys.path: {sys.path}")

# 3. 필수 라이브러리 임포트
# [FIX] 모듈 임포트 경로 표준화 및 불필요한 임포트 제거
try:
    print("Loading fonts and styles...")
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtGui import QIcon
    from output_detail_tab import OutputDetailTab 
    
    # app_style 임포트 확인
    import app_style
    print(f"[DEBUG] app_style imported from: {app_style.__file__}")
    from app_style import register_fonts, get_main_stylesheet
    
except Exception as e:
    error_msg = f"CRITICAL IMPORT ERROR:\n{str(e)}\n\n{traceback.format_exc()}"
    print(error_msg) # 콘솔에도 출력
    # 0x10 is MB_ICONHAND (Error) in Windows API
    msgbox("Startup Error", error_msg, 0x10) 
    sys.exit(1)

def main():
    # Write debug info to file IMMEDIATELY
    debug_file = None
    try:
        debug_file = open("app_startup_debug.txt", "w", encoding="utf-8")
        debug_file.write(f"=== OASIS Startup Debug ===\n")
        debug_file.write(f"Time: {datetime.datetime.now()}\n")
        debug_file.write(f"Python: {sys.executable}\n")
        debug_file.write(f"CWD: {os.getcwd()}\n\n")
        debug_file.flush()
        
        debug_file.write("[INFO] Starting Application...\n")
        debug_file.flush()
        
        print("[INFO] Starting Application...")
        print(f"[INFO] Current directory: {current_dir}")
        
        app = QApplication(sys.argv)
        print("[OK] QApplication created successfully")
        
        # 폰트 및 스타일
        try:
            print("[INFO] Registering fonts...")
            font_name = register_fonts(current_dir)
            print(f"[OK] Font registered: {font_name}")
            app.setStyleSheet(get_main_stylesheet(font_name))
            print("[OK] StyleSheet applied")
        except Exception as font_err:
            print(f"[WARN] Font registration failed: {font_err}")
            font_name = "새굴림"

        # 메인 윈도우 설정
        print("[INFO] Creating Main Window...")
        window = QMainWindow()
        window.setWindowTitle("오아시스 (OASIS)")
        
        # 아이콘 설정
        icon_path = os.path.join(current_dir, "assets", "icons", "오아시스_로고01.png")
        if os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))
            print(f"[OK] Window icon set: {icon_path}")
        else:
            print(f"[WARN] Icon file not found: {icon_path}")

        window.resize(1500, 920)
        window.setMinimumSize(1200, 800)
        window.move(50, 50)  # 화면 좌상단 근처에 배치
        print(f"[OK] Window created")
        
        # 탭 매니저 설정
        print("[INFO] Creating OutputDetailTab...")
        tab_manager = OutputDetailTab(window)
        print("[OK] OutputDetailTab instance created")
        
        print("[INFO] Calling create_tab()...")
        central_widget = tab_manager.create_tab()
        print(f"[OK] create_tab() returned widget")
        
        if central_widget is None:
            raise RuntimeError("create_tab() returned None!")
        
        print("[INFO] Setting central widget...")
        window.setCentralWidget(central_widget)
        print("[OK] Central widget set successfully")
        
        print("[INFO] Showing window...")
        window.show()
        window.raise_()  # 윈도우를 전면으로 가져오기
        window.activateWindow()  # 윈도우 활성화
        print("[OK] Window displayed successfully")
        print("\n" + "="*60)
        print("[SUCCESS] OASIS가 시작되었습니다.")
        print("="*60 + "\n")
        
        # 정상 실행
        debug_file.write("[INFO] Starting event loop...\n")
        debug_file.flush()
        result = app.exec()
        debug_file.write(f"[INFO] Event loop ended with code: {result}\n")
        debug_file.flush()
        sys.exit(result)

    except Exception as e:
        error_msg = f"RUNTIME ERROR:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        log_to_file(error_msg)
        debug_file.write(f"ERROR: {error_msg}\n")
        debug_file.flush()
        msgbox("Runtime Error", error_msg, 0x10)
        # sys.exit(1) # Don't exit immediately, allow user to see console
    
    finally:
        # 반드시 파일 닫기
        if debug_file:
            debug_file.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_to_file(f"CRITICAL MAIN FAILURE: {e}\n{traceback.format_exc()}")
        print(f"CRITICAL MAIN FAILURE: {e}")
        traceback.print_exc()
    
    print("Press Enter to exit...")
    log_to_file("Waiting for user input to exit...")
    input()

