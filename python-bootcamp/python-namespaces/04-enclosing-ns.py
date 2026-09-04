def outer():
    name = "Naresh"

    def inner():
        print(name)  # found in enclosing namespace

    inner()

outer()

if __name__ == "__main__":
    outer()