import sys
import io
# Force UTF-8 output on Windows consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000,
                 allow_unsafe_werkzeug=True, use_reloader=False)
