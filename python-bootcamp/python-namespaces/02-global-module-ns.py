# my_module.py
x = 10  # lives in the global namespace of my_module

def show():
    print(x)  # found via Global lookup

if __name__ == "__main__":
    show()