import sys
import os

def check_env():
    print(f"Python Version: {sys.version}")
    print(f"Current Working Directory: {os.getcwd()}")
    
    try:
        import ortools
        print("✅ Google OR-Tools: INSTALADO")
    except ImportError:
        print("❌ Google OR-Tools: NO ENCONTRADO (Instalar con 'pip install ortools')")

    try:
        import folium
        print("✅ Folium: INSTALADO")
    except ImportError:
        print("❌ Folium: NO ENCONTRADO")

if __name__ == "__main__":
    check_env()
