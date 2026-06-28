import uvicorn
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='PI Manager Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port number (default: 8000)')
    args = parser.parse_args()
    
    print("=== PI Manager Starting ===")
    print(f"Python version: {sys.version}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    
    # Handle PyInstaller path
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
        print(f"Running from PyInstaller, MEIPASS: {base_dir}")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Running from source, base_dir: {base_dir}")
    
    print(f"Current directory: {os.getcwd()}")
    
    # Change to base_dir
    os.chdir(base_dir)
    print(f"Changed to directory: {os.getcwd()}")
    
    # Create data directory in the executable's directory (not in MEIPASS)
    if hasattr(sys, '_MEIPASS'):
        exe_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(exe_dir, "data")
    else:
        data_dir = os.path.join(base_dir, "data")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")
    
    sys.path.insert(0, base_dir)
    print(f"sys.path[0]: {sys.path[0]}")
    
    print("Listing base_dir contents:")
    for item in os.listdir(base_dir):
        print(f"  {item}")
    
    print("Importing main module...")
    try:
        from main import app
        print("Successfully imported app")
    except Exception as e:
        print(f"Error importing main: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        return
    
    print("Starting uvicorn server...")
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=False
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
