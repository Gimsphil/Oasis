import sys
with open("python_test_output.txt", "w") as f:
    f.write("Python is working!\n")
    f.write(f"Version: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
print("This should go to stdout")
