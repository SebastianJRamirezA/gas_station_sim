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
GAS_PUMP_NUM = 4
STATION_TANK_SIZE = 500   # Size of the gas station tank (liters)
THRESHOLD = 25             # Station tank minimum level (% of full)
CAR_TANK_SIZE = 50         # Size of car fuel tanks (liters)
CAR_TANK_LEVEL = [5, 25]   # Min/max levels of car fuel tanks (liters)
REFUELING_SPEED = 2        # Rate of refuelling car fuel tank (liters / second)
T_INTER = 30               # Interval between car arrivals (seconds)
SIM_TIME = 1000            # Simulation time (seconds)
# fmt: on

REMAINING_FUEL = STATION_TANK_SIZE

class Car(object):
    def __init__(self, env, stats, name, gas_station):
        self.env = env
        self.stats = stats
        self.name = name
        self.gas_station = gas_station
        # Start the run process everytime an instance is created.
        self.action = env.process(self.run())
        self.arrival_time = 0

    def run(self):
        """A car arrives at the gas station for refueling.

        It requests one of the gas station's fuel pumps and tries to get the
        desired amount of fuel from it.

        """
        global REMAINING_FUEL

        if not_fuel_remaining.triggered:
            return
        
        gas_pump = min(gas_station, key=lambda s: (s.count + len(s.queue)))

        self.arrival_time = self.env.now
        self.stats.add_new_client(self.arrival_time)
        car_tank_level = random.randint(*CAR_TANK_LEVEL)
        print(f'{self.env.now:6.1f} s: {self.name} arrived at gas station')
        with gas_pump.request() as req:
            # Request one of the gas pumps
            yield req

            if (REMAINING_FUEL / STATION_TANK_SIZE) * 100 > THRESHOLD: 

                # Get the required amount of fuel
                fuel_required = CAR_TANK_SIZE - car_tank_level
                self.stats.serve_client(self.env.now)
                self.stats.add_time_on_queue(self.env.now - self.arrival_time)

                if ((REMAINING_FUEL - fuel_required) / STATION_TANK_SIZE) * 100 > THRESHOLD:

                    REMAINING_FUEL -= fuel_required
                    yield env.timeout(fuel_required/REFUELING_SPEED)
                    print(f'{self.env.now:6.1f} s: {self.name} refueled with {fuel_required:.1f}L')

                else: 

                    fuel_required = REMAINING_FUEL - STATION_TANK_SIZE * (THRESHOLD/100)
                    REMAINING_FUEL -= fuel_required
                    yield env.timeout(fuel_required/REFUELING_SPEED)
                    print(f'{self.env.now:6.1f} s: {self.name} refueled only with {fuel_required:.1f}L before the fuel ran out')
                
                self.stats.leave_system(self.env.now)
                self.stats.add_time_on_system(self.env.now - self.arrival_time)

            else: 

                print(f'{self.env.now:6.1f} s: {self.name} leaves. Not remaining fuel')

                not_fuel_remaining.succeed()


def car_generator(env, gas_station, stats):
    """Generate new cars that arrive at the gas station."""
    for i in itertools.count():
        yield env.timeout(random.expovariate(1.0 / T_INTER))
        c = Car(env, stats, f'Car {i}', gas_station)

# Setup and start the simulation
print('Gas Station refuelling')
random.seed(RANDOM_SEED)

stats = ClientStatsAccumulator()

# Create environment and start processes
env = simpy.Environment()
gas_station = [simpy.Resource(env, capacity=1) for _ in range(GAS_PUMP_NUM)]
env.process(car_generator(env, gas_station, stats))

gas_station_close_event = env.timeout(SIM_TIME)
not_fuel_remaining = simpy.Event(env)

main_event = env.any_of([gas_station_close_event, not_fuel_remaining])

# Execute!
env.run(until=main_event)

if not_fuel_remaining.triggered:

    print('\nSimulation results after {:.1f} seconds (Not remaining fuel):'.format(env.now))

else: 

    print('\nSimulation results after {:.1f} seconds:'.format(SIM_TIME))

# Print statistics

stats.print_statistics(SIM_TIME)