def greet():
    message = "Hi there"  # local to greet()
    print(message)

greet()
print(message)  # NameError: 'message' isn't visible outside the function

if __name__ == "__main__":
    greet()