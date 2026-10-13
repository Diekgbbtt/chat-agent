"""Starts the chatbot. Do not rename: the online evaluation runs this file."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "additional_files"))

from agent.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
