import random


class Node:
    def __init__(self, id):
        self.id = id
        self.x = 0
        self.y = 0

    def __repr__(self):
        return f'Node({self.id}, x={self.x}, y={self.y})'

    def move(self, x, y):
        self.x = x
        self.y = y


class Env:
    def __init__(self):
        self.nodes = []
        self.t = 0

    def generate_nodes(self, population):
        for i in range(population):
            self.nodes.append(Node(i))

    def show_nodes(self):
        for node in self.nodes:
            print(node)


if __name__ == '__main__':
    env = Env()
    print(f'simulation started... t={env.t}')
    env.generate_nodes(10)
    env.show_nodes()