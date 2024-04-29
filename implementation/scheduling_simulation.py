import simpy
import random
from datetime import datetime, date
import csv
import time
import yaml
import pandas
import numpy as np
from dataclasses import dataclass
from typing import List, Iterator, Type

class Job:
    def __init__(self, env: simpy.Environment, id, deadline: simpy.core.SimTime, runtime: simpy.core.SimTime):
        all_jobs.append(self)
        self.id = id
        self.deadline = deadline
        self.runtime = runtime
        self.env = env
        self.log = {
            'submit_time': env.now,
            'start_time': None,
            'end_time': None,
        }

    def do_something(self):
        self.log.update({'start_time': self.env.now})
        yield self.env.timeout(self.runtime)
        self.log.update({'end_time': self.env.now})

class ComputeNode:
    def __init__(self, env: simpy.Environment, id, cost_shutdown, duration_shutdown, cost_boot, duration_boot, scheduler):
        self.id = id
        self.cost_shutdown = cost_shutdown

        self.ressource = simpy.Resource(env, 1)
        self.env = env
        self.last_logging_event = env.now
        self.scheduler = scheduler

        self.shutdown_duration = config.shutdown_duration
        self.duration_boot = config.boot_duration
        self.idle_power_hour = config.idle_power_hour
        self.working_power_per_hour = config.working_power_per_hour
        self.offline_power_per_hour = config.offline_power_per_hour
        self.shutdown_power_per_hour = config.shutdown_power_per_hour
        self.starting_power_per_hour = config.starting_power_per_hour

        self.state: 'READY' | 'SHUTDOWN' | 'STARTING' | 'WORKING' | 'OFFLINE' = None
        self.set_state('READY')

    def set_state(self, state: str):
        self.state = state
        log.get('compute_node_dataframe').append({'id': self.id, 'timestamp': self.env.now, 'power': self.get_current_power(), 'state': self.state})


    def execute_job(self, job: Job):
        with self.ressource.request() as request:
            self.set_state('WORKING')
            start_time = self.env.now
            yield request
            yield self.env.process(job.do_something())
            end_time = self.env.now
            log.get('compute_node_events').append({'type': 'execute_job', 'id': 'Node' + str(self.id), 'start': start_time, 'end': end_time, 'time': end_time - start_time, 'job': job})
            self.set_state('READY')
            self.scheduler.schedule_jobs()
    
    def get_current_power(self) -> int:
        match self.state:
            case 'READY':
                return self.idle_power_hour
            case 'SHUTDOWN':
                return self.shutdown_power_per_hour
            case 'STARTING':
                return self.starting_power_per_hour
            case 'OFFLINE':
                return self.offline_power_per_hour
            case 'WORKING':
                return self.working_power_per_hour
            case _:
                return NULL

class BaseScheduler:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.nodes: List[ComputeNode] = [ComputeNode(env, i, 1,2,3,4, self) for i in range(config.number_of_compute_nodes)]
        self.queue: List[Job] = []

    def get_waiting_jobs() -> List[Job]:
        pass

    def submit_job(self, job: Job):
        self.queue.append(job)
        log.get('job_queue').append({'type': 'append', 'time': self.env.now, 'length': len(self.queue)})
        self.schedule_jobs()

    def get_compute_nodes() -> List[ComputeNode]:
        pass

    def get_carbon_intensity_at_timestamp(timestamp: int) -> float:
        pass

    def schedule_jobs() -> None:
        pass

class FiFoScheduler(BaseScheduler):
    """
    FiFo (First In First Out) Scheduler executes jobs whenever ComputeNodes are ready.
    This is supposed to simulate a "dumb" Scheduler, that does not take advantage of 
    different Co2 levels.
    """

    def schedule_jobs(self):
        while len(self.queue) > 0:
            job = self.queue.pop()
            log.get('job_queue').append({'type': 'pop', 'time': self.env.now, 'length': len(self.queue)})
            first_available_compute_node: ComputeNode = next((node for node in self.nodes if node.state == 'READY'), None)
            if (first_available_compute_node is None):
                self.queue.append(job)
                break
            first_available_compute_node.state = 'STARTING'
            self.env.process(first_available_compute_node.execute_job(job))

class SimpleGreenScheduler(BaseScheduler):
    """
    Similar to the scheduler suggested by the Paper "GreenSlot: Scheduling Energy Consumption in Green Datacenters",
    this scheduler executes jobs preferably during times of high co2-efficiency. Only if deadlines cannot be met otherwise,
    work jobs for cheap brown energy. For simpleness' sake, we don't model the cost of energy here, so executing jobs on high brown energy 
    will be done whenever.

    In the original paper, green energy is supplied via a solar array. In our model, we check for intervals where co2 production is
    low-ish.
    """

    def add_row_to_scheduling_matrix(self, timestamp: int):
        predicted_co2 = carbon_predictor.get_carbon_intensity_at_timestamp(timestamp)
        self.scheduling_matrix.loc[timestamp] = [timestamp, predicted_co2] + ['READY' for i in range(0, config.number_of_compute_nodes)]

    def __init__(self, env: simpy.Environment):
        super().__init__(env)

        """
        We keep our current state in a matrix

        +-----------+----------+------------+------------+-----+
        | Timestamp | gCo2/kWh | StateNode1 | StateNode2 | ... |
        +-----------+----------+------------+------------+-----+
        | T1        |      134 | READY      | READY      |     |
        | T2        |      129 | Start Job1 | READY      |     |
        | T2        |      135 | Job1       | READY      |     |
        +-----------+----------+------------+------------+-----+

        which contains the model on what we schedule. This will be a scrolling window over time
        with past-timestamp-rows continually being discarded when possible.
        """

        columns = ['Timestamp', 'gCo2/kWh'] + ['StateNode' + str(index) for index in range(0, config.number_of_compute_nodes)]
        self.scheduling_matrix = pandas.DataFrame(columns=columns)
        self.scheduling_matrix.set_index('Timestamp')     
        self.add_row_to_scheduling_matrix(env.now)  

    def schedule_jobs(self):
        # Look at 10 minute scheduling windods where jobs may start
        # update our prediction window if needed
        last_timestamp = self.scheduling_matrix.iloc[len(self.scheduling_matrix) - 1]['Timestamp']

        # schedule for 2 days ahead  
        while (last_timestamp - self.env.now < (2 * 24 * 60 * 60)):
            last_timestamp += 10 * 60
            self.add_row_to_scheduling_matrix(last_timestamp)

        # remove rows that are in the past
        past_rows_mask = self.scheduling_matrix['Timestamp'] < self.env.now
        self.scheduling_matrix.drop(self.scheduling_matrix[past_rows_mask].index, inplace=True)

        # schedule the next jobs
        while len(self.queue) > 0:
            job = self.queue.pop()
            log.get('job_queue').append({'type': 'pop', 'time': self.env.now, 'length': len(self.queue)})
            average_co2 = self.scheduling_matrix['gCo2/kWh'].mean()
            # find timeslots that have below average co2 emissions
            node_is_available = np.array([False] * config.number_of_compute_nodes)
            start_of_timeslot = np.array([None] * config.number_of_compute_nodes)

            found_slot = False
            for index, row in self.scheduling_matrix.iterrows():
                if (found_slot is True):
                    break
                for i in range(0, config.number_of_compute_nodes):
                    # the slot starts here

                    label_of_node = 'StateNode'+ str(i)
                    state_of_node = row[label_of_node]
                    if (start_of_timeslot[i] == None and state_of_node == 'READY' and row['gCo2/kWh']<average_co2):
                        start_of_timeslot[i] = row['Timestamp'] 
                    elif (start_of_timeslot[i] != None and state_of_node != 'READY' or row['gCo2/kWh']>average_co2):
                        start_of_timeslot[i] = None

                    if  (start_of_timeslot[i] is not None and (row['Timestamp'] - start_of_timeslot[i]) > job.runtime):
                        # we can schedule the job here

                        is_first = True

                        for index, row_to_be_updated in self.scheduling_matrix.loc[start_of_timeslot[i] : row['Timestamp']].iterrows():
                            if (is_first):
                                is_first = False
                                self.scheduling_matrix.at[index, label_of_node] = job
                                continue
                            self.scheduling_matrix.at[index, label_of_node] = 'WORKING'

                        found_slot = True    
                        break # out of searching for a timeslot
            if (found_slot is False):
                self.queue.append(job)

        # we now planned on when to execute all jobs, now we need to actually start them too
        schedule_to_be_executed = self.scheduling_matrix.iloc[0]
        if (schedule_to_be_executed['Timestamp'] > self.env.now):
            return

        for i in range(0, config.number_of_compute_nodes):
            value_of_plan = schedule_to_be_executed['StateNode'+ str(i)] 
            if (isinstance(value_of_plan, Job)):
                self.env.schedule()
                self.env.process(self.nodes[i].execute_job(value_of_plan))

@dataclass
class SimulationConfig:
    scheduler: Type[BaseScheduler] = None

    simulation_start: int = time.mktime(date.fromisocalendar(year=2023, week=1, day=1).timetuple())
    simulation_length: int = 24 * 60 * 60

    number_of_compute_nodes: int = 10
    submit_interval_generator_scale: int = 600
    job_length_generator_mean: int = 3600
    job_length_generator_scale: int = 1800

    idle_power_hour: float = 5
    working_power_per_hour: float = 10
    offline_power_per_hour: float = 1
    shutdown_power_per_hour: float = 8
    starting_power_per_hour: float = 5
    boot_duration: int = 30
    shutdown_duration: int = 60


config: SimulationConfig = None

carbon_predictor = None

class CarbonEmissionPredictor:
    def __init__(self):
        self.carbon_data = pandas.read_csv('data/DE_2023_hourly.csv', delimiter=',')
        self.carbon_data['timestamp'] = self.carbon_data['Datetime (UTC)'].apply(lambda datetime_string: datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S").timestamp())

    # We run a linear interpolation between those points
    def get_carbon_intensity_at_timestamp(self, timestamp: int) -> int:
        return np.interp(x = timestamp, xp=self.carbon_data['timestamp'], fp=self.carbon_data['Carbon Intensity gCO₂eq/kWh (direct)'])

class Scheduler:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.nodes: List[ComputeNode] = [ComputeNode(env, i, 1,2,3,4, self) for i in range(config.number_of_compute_nodes)]

        self.queue: List[Job] = []
        self.env = env

    def submit_job(self, job: Job):
        self.queue.append(job)
        log.get('job_queue').append({'type': 'append', 'time': self.env.now, 'length': len(self.queue)})

        self.schedule_jobs()

    def schedule_jobs(self):
        while len(self.queue) > 0:
            job = self.queue.pop()
            log.get('job_queue').append({'type': 'pop', 'time': self.env.now, 'length': len(self.queue)})
            first_available_compute_node: ComputeNode = next((node for node in self.nodes if node.state == 'READY'), None)
            if (first_available_compute_node is None):
                self.queue.append(job)
                break
            first_available_compute_node.state = 'STARTING'
            self.env.process(first_available_compute_node.execute_job(job))


class JobSubmitter:
    def __init__(self, env: simpy.Environment, scheduler: BaseScheduler):
        self.env = env
        self.scheduler = scheduler

    def generate_jobs(self):
        pass

class RandomJobSubmitter(JobSubmitter):

    def generate_jobs(env, scheduler):
        job_id = 0
        rng = np.random.default_rng(seed=0)

        while True:
            job_id += 1
            runtime = round(rng.normal(loc=config.job_length_generator_mean, scale=config.job_length_generator_scale))
            if runtime < 5:
                    runtime = 5
                # Assume, the job is atleast runnable
            deadline = runtime + rng.integers(0, 100)
            job = Job(env, id, 1, deadline, runtime)
            scheduler.submit_job(job)
            wait_time_until_next_job = rng.exponential(scale=config.submit_interval_generator_scale)
            yield env.timeout(wait_time_until_next_job)  # Generate new job every 60 seconds
            # random.expovariate(1.0 / 5)

class YamlJobSubmitter(JobSubmitter):
    def __init__(self, env: simpy.Environment, scheduler: BaseScheduler, workload_path: str):
        self.env = env
        self.scheduler = scheduler
        self.workload_path = workload_path

    def generate_jobs(self):
        jobs = []
        with open('workloads/two_jobs.yml', 'r') as file:
            parsed = yaml.safe_load(file)
            for job in parsed:
                jobs.append({'start': int(job['start']), 'length': int(job['length']), 'deadline': int(job['deadline'])})
        jobs_sorted_by_start = sorted(jobs, key=lambda x: x['start'])

        yield self.env.timeout(jobs_sorted_by_start[0]['start'])
        for i in range(0, len(jobs_sorted_by_start)):
            job_config = jobs_sorted_by_start[i]
            runtime = job_config['length']
            deadline = runtime + job_config['deadline']
            job = Job(self.env, id, deadline, runtime)
            self.scheduler.submit_job(job)

            if (i + 1 == len(jobs_sorted_by_start)):
                continue

            wait_time_until_next_job = config.simulation_start + jobs_sorted_by_start[i+1]['start'] - self.env.now
            yield self.env.timeout(wait_time_until_next_job)

all_jobs = []

log = {
    'job_queue': [],
    'scheduler_events': [],
    'compute_node_dataframe': [],
    'compute_node_events': [],
    'scheduler_events': []
}

def run_simulation(simulation_config: SimulationConfig):
    global config
    config = simulation_config

    global carbon_predictor
    carbon_predictor = CarbonEmissionPredictor()

    # Simulation setup
    simulation_start_time_timestamp = config.simulation_start
    simulation_end_time_timestamp = simulation_start_time_timestamp + config.simulation_length

    #test = CarbonEmissionSensor('data/DE_2023_hourly.csv')
    env = simpy.Environment(simulation_start_time_timestamp) # create a new env for each simulation
    scheduler = config.scheduler(env)

    # Start job generator process
    job_submitter = YamlJobSubmitter(env, scheduler, 'workloads/two_jobs.yml')
    env.process(job_submitter.generate_jobs())

    # Run simulation
    env.run(until=simulation_end_time_timestamp)

def get_log():
    return log

if __name__ == "__main__":
    run_simulation()