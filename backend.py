"""Compatibility launcher. New development belongs in app/."""
import os
from run import app
if __name__ == '__main__':
    app.run(host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','5000')),debug=False)
