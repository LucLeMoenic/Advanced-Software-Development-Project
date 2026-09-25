import os
import sys

RAG_SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAG_SERVER_DIR not in sys.path:
    sys.path.insert(0, RAG_SERVER_DIR)
