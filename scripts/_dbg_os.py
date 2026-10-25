import os
import sys
print("os:", os.__file__)
print("os.path:", os.path)
print("has dirname:", hasattr(os.path, "dirname"))
print("sys.path[0]:", sys.path[0])
