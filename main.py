from simulation import Simulation

if __name__ == '__main__':
    sim = Simulation(size_meters=(100.0, 100.0, 2.0))

    sim.generate_random_nodes(20)

    sim.run(steps=3000, dt_seconds=0.2, visualize=True)
