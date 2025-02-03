import random

class Node:
    def __init__(self):
        self.id = random.randint(1,40)

class Env:
    def __init__(self):
        self.id = 0


def create_env():
    """Instantiate an environment of nodes with coordinates at time t=0.

    Returns::
    <Env>
    """

def move(node, x, y):
    """Move a particular node to: (x, y) from: current location.

    Parameters::
    node : <Node>
    x : int
    y : int

    Returns::
    <Null>
    """

def main():
    """
    """
    print("simulation started... t=0")

if __name__ == "__main__":
    main()