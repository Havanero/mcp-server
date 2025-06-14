#!/usr/bin/env python3
"""
Quick dependency check and transport test
"""
import sys


def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking MCP Transport Dependencies")
    print("-" * 40)
    
    deps = [
        ("websockets", "WebSocket transport"),
        ("aiohttp", "HTTP transport"),
    ]
    
    missing = []
    for module, description in deps:
        try:
            __import__(module)
            print(f"✅ {module:12} - {description}")
        except ImportError:
            print(f"❌ {module:12} - {description} (MISSING)")
            missing.append(module)
    
    if missing:
        print(f"\n📦 Install missing dependencies:")
        print(f"   pip install {' '.join(missing)}")
        print(f"   # Or install all: pip install -r requirements.txt")
        return False
    else:
        print(f"\n✅ All dependencies available!")
        return True


def show_quick_start():
    """Show quick start commands"""
    print(f"\n🚀 Quick Start Commands")
    print("=" * 50)
    
    print(f"📡 Stdio Transport (Development):")
    print(f"   python3 server_v2.py")
    print(f"   python3 ../mcp-client/cli.py python3 server_v2.py")
    
    print(f"\n🌐 WebSocket Transport (Production):")
    print(f"   python3 server_websocket.py")
    print(f"   python3 websocket_client.py")
    
    print(f"\n🔗 HTTP Transport (REST API):")
    print(f"   python3 server_http.py")
    print(f"   curl http://localhost:8080/tools")
    print(f"   open http://localhost:8080/client")
    
    print(f"\n🧪 Test All Transports:")
    print(f"   python3 test_transports.py")
    
    print(f"\n📚 Documentation:")
    print(f"   cat TRANSPORTS.md")
    print(f"   cat DECORATORS.md")


if __name__ == "__main__":
    deps_ok = check_dependencies()
    show_quick_start()
    
    if not deps_ok:
        sys.exit(1)
    else:
        print(f"\n🎉 Ready to go! Choose your transport and start building!")
