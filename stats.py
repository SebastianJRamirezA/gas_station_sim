class ClientStatsAccumulator():
    def __init__(self):
        self.time_on_queue = []
        self.time_on_system = []

        self.current_clients_on_queue = 0
        self.current_clients_on_system = 0
        self.last_change_on_queue = 0
        self.last_change_on_system = 0

        self.accum_queue = 0
        self.accum_system = 0

    def add_time_on_queue(self, time):
        self.time_on_queue.append(time)

    def add_time_on_system(self, time):
        self.time_on_system.append(time)

    def add_new_client(self, now):
        self.accum_queue += self.current_clients_on_queue * (now - self.last_change_on_queue)
        self.accum_system += self.current_clients_on_system * (now - self.last_change_on_system)

        self.last_change_on_queue = now
        self.last_change_on_system = now
        self.current_clients_on_queue += 1
        self.current_clients_on_system += 1

    def serve_client(self, now):
        self.accum_queue += self.current_clients_on_queue * (now - self.last_change_on_queue)
        self.last_change_on_queue = now
        self.current_clients_on_queue -= 1

    def leave_system(self, now):
        self.accum_system += self.current_clients_on_system * (now - self.last_change_on_system)
        self.last_change_on_system = now
        self.current_clients_on_system -= 1

    def get_average_clients_on_queue(self, total_time):
        return self.accum_queue / total_time

    def get_average_clients_on_system(self, total_time):
        return self.accum_system / total_time

    def get_average_time_on_queue(self):
        return sum(self.time_on_queue) / len(self.time_on_queue)

    def get_average_time_on_system(self):
        return sum(self.time_on_system) / len(self.time_on_system)
    
    def print_statistics(self, total_time):
        print("Average number of clients on queue: {:.2f}".format(self.get_average_clients_on_queue(total_time)))
        print("Average number of clients on system: {:.2f}".format(self.get_average_clients_on_system(total_time)))
        print("Average time on queue: {:.2f} seconds".format(self.get_average_time_on_queue()))
        print("Average time on system: {:.2f} seconds".format(self.get_average_time_on_system()))