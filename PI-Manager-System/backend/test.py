import sys
import os

print("=== Test Script ===")
print(f"Python version: {sys.version}")
print(f"sys.executable: {sys.executable}")
print(f"Has _MEIPASS: {hasattr(sys, '_MEIPASS')}")
if hasattr(sys, '_MEIPASS'):
    print(f"MEIPASS: {sys._MEIPASS}")
print(f"Current directory: {os.getcwd()}")
print("Test completed successfully!")
input("Press Enter to exit...")
