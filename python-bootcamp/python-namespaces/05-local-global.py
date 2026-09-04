x = "global x"

def outer():
    x = "enclosing x"

    def inner():
        x = "local x"
        print(x)  # prints "local x" -- local wins first

    inner()
    print(x)  # prints "enclosing x"

outer()
print(x)  # prints "global x"

if __name__ == "__main__":
    outer()
