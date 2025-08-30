import sys

from app import app

# Main application entry point
if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1] == "--port":
        try:
            port = int(sys.argv[2])
        except (IndexError, ValueError):
            pass
    app.run(host="0.0.0.0", port=port, debug=True)
