class Dog:
    species = "Canis familiaris"  # class namespace

    def __init__(self, name):
        self.name = name  # instance namespace (self.__dict__)

if __name__ == "__main__":
    d = Dog("Rex")
    print(Dog.__dict__)   # class namespace as a dict

    print("-----------------")
    print(d.__dict__)     # instance namespace as a dict