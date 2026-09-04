def demo():
    a = 1
    b = 2
    print(locals())  # {'a': 1, 'b': 2}

demo()
print(globals())  # shows all global names, e.g. '__name__', 'x', 'demo', ...

if __name__ == "__main__":
    demo()