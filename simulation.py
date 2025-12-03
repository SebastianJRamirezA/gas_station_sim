"""
Gas Station Simulation
---------------------------------
Description:
  This model simulates the operation of a gas station with multiple pumps (servers)
  and a shared central storage tank.
  
  Key Features:
  1. Arrivals: Random following an exponential distribution (Poisson Process).
  2. Queues: Multiple queues (one per pump).
  3. Queue Selection: The client chooses the pump with the lowest load (Load Balancing).
  4. Service Time: Random following a Normal distribution.
  5. Constraint: Service depends on fuel availability in the central tank.

Authors: [Frontino Tech]
Date: [2025]
"""

import itertools
import random
import pandas as pd
import simpy

from stats import ClientStatsAccumulator

# fmt: off
RANDOM_SEED = 42
NUM_PUMPS = 4
STATION_TANK_SIZE = 72000   # Size of the gas station tank (liters)
THRESHOLD = 20             # Station tank minimum level (% of full)
CAR_TANK_LIMITS = [9, 140]   # Min/max levels of car fuel tanks (liters)
SIM_TIME = 1440            # Simulation time (minutes)
LAMBDA_PARAM = 0.4364009754845333
SERVICE_TIME_MEAN = 4.3096774193548395
SERVICE_TIME_VARIANCE = pow(2.926779011099522,2)
CAR_TANK_MEAN = 51.3421052631579
CAR_TANK_VARIANCE = pow(29.185681705598356,2)
# fmt: on

REMAINING_FUEL = STATION_TANK_SIZE

class Car(object):
    """
    Represents a vehicle arriving at the gas station.
    Each vehicle is a process that interacts with the environment and resources.
    """
    def __init__(self, env, stats, name, gas_station):
        self.env = env
        self.stats = stats
        self.name = name
        self.gas_station = gas_station
        # Start the vehicle execution process upon instantiation
        self.action = env.process(self.run())
        self.arrival_time = 0

    def run(self):
        """
        Main logic of the client lifecycle in the system:
        Arrival -> Queue Selection -> Waiting -> Service -> Departure
        """
        global REMAINING_FUEL

        # 1. Check if the station has already closed due to lack of fuel
        if not_fuel_remaining.triggered:
            return
        
        # 2. Pump Selection (Routing Strategy)
        # The driver chooses the pump with the lowest load (cars in service + cars in queue).
        # This simulates rational "Load Balancing" behavior.
        gas_pump = min(gas_station, key=lambda s: (s.count + len(s.queue)))

        # Record arrival time and update statistics
        self.arrival_time = self.env.now
        self.stats.add_new_client(self.arrival_time)
        
        # Determine how much fuel this specific vehicle needs
        fuel_required = random.normalvariate(CAR_TANK_MEAN, CAR_TANK_VARIANCE)
        while fuel_required < CAR_TANK_LIMITS[0] or fuel_required > CAR_TANK_LIMITS[1]:
            fuel_required = random.normalvariate(CAR_TANK_MEAN, CAR_TANK_VARIANCE)
        print(f'{self.env.now:6.1f} m: {self.name} arrived at gas station')
        with gas_pump.request() as req:
            # Wait until the pump is free (Service turn)
            yield req

            # 4. Inventory and Service Logic
            # Check if the central tank level is above the operational threshold
            if (REMAINING_FUEL / STATION_TANK_SIZE) * 100 > THRESHOLD: 

                # Vehicle starts being served
                self.stats.serve_client(self.env.now)
                # Record time spent in queue (Wq)
                self.stats.add_time_on_queue(self.env.now - self.arrival_time)

                # Deduct fuel from global inventory
                # If there is enough to fill the entire requirement:
                if ((REMAINING_FUEL - fuel_required) / STATION_TANK_SIZE) * 100 > THRESHOLD:

                    REMAINING_FUEL -= fuel_required
                    # service_time = random.randint(SERVICE_TIME[0], SERVICE_TIME[1])
                    service_time = random.normalvariate(SERVICE_TIME_MEAN, SERVICE_TIME_VARIANCE)

                    while service_time < 0:
                        service_time = random.normalvariate(SERVICE_TIME_MEAN, SERVICE_TIME_VARIANCE)

                    yield env.timeout(service_time)
                    print(f'{self.env.now:6.1f} m: {self.name} refueled with {fuel_required:.1f}L')

                else: 
                    # If there isn't enough to fill completely without breaching the threshold,
                    # provide only what is available down to the threshold.
                    fuel_required = REMAINING_FUEL - STATION_TANK_SIZE * (THRESHOLD/100)
                    REMAINING_FUEL -= fuel_required

                    service_time = random.normalvariate(SERVICE_TIME_MEAN, SERVICE_TIME_VARIANCE)

                    while service_time < 0:
                        service_time = random.normalvariate(SERVICE_TIME_MEAN, SERVICE_TIME_VARIANCE)

                    yield env.timeout(service_time)
                    print(f'{self.env.now:6.1f} m: {self.name} refueled only with {fuel_required:.1f}L before the fuel ran out')
                
                # 5. Departure from System
                self.stats.leave_system(self.env.now)
                # Record total time in system (W)
                self.stats.add_time_on_system(self.env.now - self.arrival_time)

            else: 
                # If the central tank is below the threshold at the moment of service,
                # the station closure event is triggered.
                print(f'{self.env.now:6.1f} s: {self.name} leaves. Not remaining fuel')
                not_fuel_remaining.succeed()


def car_generator(env, gas_station, stats):
    """
    Creates new vehicles following a Poisson process.
    """
    for i in itertools.count():
        # Wait for a random exponential time before generating the next vehicle
        yield env.timeout(random.expovariate(LAMBDA_PARAM))
        c = Car(env, stats, f'Car {i}', gas_station)

print('--- Starting Gas Station Simulation (10 Replications) ---')
    
# Define seeds for reproducibility
random_seeds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

# Setup DataFrame columns and types
data_columns = ['Run', 'Seed', 'Average clients on queue', 'Average clients on system', 'Average time on queue', 'Average time on system']
data_types = {
    'Run': 'int64', 
    'Seed': 'int64', 
    'Average clients on queue': 'float64', 
    'Average clients on system': 'float64', 
    'Average time on queue': 'float64', 
    'Average time on system': 'float64'
}

df = pd.DataFrame(columns=data_columns).astype(data_types)

for seed in random_seeds:
    # 1. Reset Global State for each run
    REMAINING_FUEL = STATION_TANK_SIZE
    
    # 2. Set seed
    random.seed(seed)
    
    # 3. Initialize environment and objects
    stats = ClientStatsAccumulator()
    env = simpy.Environment()
    gas_station = [simpy.Resource(env, capacity=1) for _ in range(NUM_PUMPS)]
    
    # Start processes
    env.process(car_generator(env, gas_station, stats))

    # 4. Run Simulation
    gas_station_close_event = env.timeout(SIM_TIME)     
    not_fuel_remaining = simpy.Event(env)               
    main_event = env.any_of([gas_station_close_event, not_fuel_remaining])
    
    env.run(until=main_event)

    # 5. Collect Statistics for this replication
    run_data = {
        'Run': len(df) + 1,
        'Seed': seed,
        'Average clients on queue': stats.get_average_clients_on_queue(env.now),
        'Average clients on system': stats.get_average_clients_on_system(env.now),
        'Average time on queue': stats.get_average_time_on_queue(),
        'Average time on system': stats.get_average_time_on_system()
    }
    
    # Append to DataFrame
    df.loc[len(df)] = run_data

# 6. Print Results
print("\nDataFrame Head (First 10 runs):")
print(df.head(10))

print("\nDescriptive Statistics:")
print(df.describe())
