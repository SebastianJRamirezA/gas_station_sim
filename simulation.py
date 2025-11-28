"""
Gas Station Refueling example

Covers:

- Resources: Resource
- Resources: Container
- Waiting for other processes

Scenario:
  A gas station has a limited number of gas pumps that share a common
  fuel reservoir. Cars randomly arrive at the gas station, request one
  of the fuel pumps and start refueling from that reservoir.

  A gas station control process observes the gas station's fuel level
  and calls a tank truck for refueling if the station's level drops
  below a threshold.

"""

import itertools
import random

import simpy

from stats import ClientStatsAccumulator

# fmt: off
RANDOM_SEED = 42
STATION_TANK_SIZE = 200    # Size of the gas station tank (liters)
THRESHOLD = 25             # Station tank minimum level (% of full)
CAR_TANK_SIZE = 50         # Size of car fuel tanks (liters)
CAR_TANK_LEVEL = [5, 25]   # Min/max levels of car fuel tanks (liters)
REFUELING_SPEED = 2        # Rate of refuelling car fuel tank (liters / second)
TANK_TRUCK_TIME = 300      # Time it takes tank truck to arrive (seconds)
T_INTER = 30               # Interval between car arrivals (seconds)
SIM_TIME = 1000            # Simulation time (seconds)
# fmt: on

class Car(object):
    def __init__(self, env, stats, name, gas_station, station_tank):
        self.env = env
        self.stats = stats
        self.name = name
        self.gas_station = gas_station
        self.station_tank = station_tank
        # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        self.arrival_time = 0

    def run(self):
        """A car arrives at the gas station for refueling.

        It requests one of the gas station's fuel pumps and tries to get the
        desired amount of fuel from it. If the station's fuel tank is
        depleted, the car has to wait for the tank truck to arrive.

        """
        self.arrival_time = self.env.now
        self.stats.add_new_client(self.arrival_time)
        car_tank_level = random.randint(*CAR_TANK_LEVEL)
        print(f'{self.env.now:6.1f} s: {self.name} arrived at gas station')
        with gas_station.request() as req:
            # Request one of the gas pumps
            yield req

            # Get the required amount of fuel
            fuel_required = CAR_TANK_SIZE - car_tank_level
            self.stats.serve_client(self.env.now)
            self.stats.add_time_on_queue(self.env.now - self.arrival_time)
            yield station_tank.get(fuel_required)

            # The "actual" refueling process takes some time
            yield self.env.timeout(fuel_required / REFUELING_SPEED)
            self.stats.leave_system(self.env.now)
            self.stats.add_time_on_system(self.env.now - self.arrival_time)
            print(f'{self.env.now:6.1f} s: {self.name} refueled with {fuel_required:.1f}L')

def gas_station_control(env, station_tank):
    """Periodically check the level of the gas station tank and call the tank
    truck if the level falls below a threshold."""
    while True:
        if station_tank.level / station_tank.capacity * 100 < THRESHOLD:
            # We need to call the tank truck now!
            print(f'{env.now:6.1f} s: Calling tank truck')
            # Wait for the tank truck to arrive and refuel the station tank
            yield env.process(tank_truck(env, station_tank))

        yield env.timeout(10)  # Check every 10 seconds


def tank_truck(env, station_tank):
    """Arrives at the gas station after a certain delay and refuels it."""
    yield env.timeout(TANK_TRUCK_TIME)
    amount = station_tank.capacity - station_tank.level
    station_tank.put(amount)
    print(
        f'{env.now:6.1f} s: Tank truck arrived and refuelled station with {amount:.1f}L'
    )


def car_generator(env, gas_station, station_tank, stats):
    """Generate new cars that arrive at the gas station."""
    for i in itertools.count():
        yield env.timeout(random.expovariate(1.0 / T_INTER))
        c = Car(env, stats, f'Car {i}', gas_station, station_tank)

# Setup and start the simulation
print('Gas Station refuelling')
random.seed(RANDOM_SEED)

stats = ClientStatsAccumulator()

# Create environment and start processes
env = simpy.Environment()
gas_station = simpy.Resource(env, 2)
station_tank = simpy.Container(env, STATION_TANK_SIZE, init=STATION_TANK_SIZE)
env.process(gas_station_control(env, station_tank))
env.process(car_generator(env, gas_station, station_tank, stats))

# Execute!
env.run(until=SIM_TIME)

# Print statistics
print('\nSimulation results after {:.1f} seconds:'.format(SIM_TIME))
stats.print_statistics(SIM_TIME)