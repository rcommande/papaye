import multiprocessing
import pickle
import traceback
import zmq

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
from pyramid.registry import global_registry
from termcolor import colored

from papaye.tasks import TaskRegistry


class Device(multiprocessing.Process):

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.go = True

    def get_socket(self):
        raise NotImplemented()

    def run(self):
        raise NotImplemented()


class Scheduler(Device):

    def __init__(self, settings):
        super().__init__(settings)
        self.settings = settings
        self.concurency = int(self.settings.get('worker.concurency', 1))

    def run(self):
        try:
            processes = []
            processes.append(QueueDevice(self.settings))
            processes.append(CollectorDevice(self.settings))
            for index in range(1, self.concurency + 1):
                processes.append(ConsumerDevice(self.settings, index))

            for process in processes:
                process.start()

            for process in processes:
                process.join()
        except KeyboardInterrupt:
            pass


class Producer(object):

    def __init__(self, settings):
        self.settings = settings
        self.socket = self.get_socket()

    def get_socket(self):
        context = zmq.Context()
        socket = context.socket(zmq.XREQ)
        socket.connect(self.settings.get('proxy.broker'))
        return socket


class ConsumerDevice(Device):

    def __init__(self, settings, worker_number):
        super().__init__(settings)
        self.worker_number = worker_number
        # Load tasks
        __import__("papaye.tasks.download")

    def get_sockets(self):
        context = zmq.Context()
        socket = context.socket(zmq.XREP)
        socket.connect(self.settings.get('proxy.worker_socket'))
        socket2 = context.socket(zmq.PUSH)
        socket2.connect(self.settings.get('proxy.collector_socket'))
        return socket, socket2

    def run(self):
        self.worker_socket, self.collector_socket = self.get_sockets()
        worker_number = self.worker_number
        while self.go:
            try:
                data = self.worker_socket.recv_multipart()[2]
                task_id, func_name, args, kwargs = pickle.loads(data)
                func = TaskRegistry()._tasks[func_name]
                func.task_id = task_id
                print(colored('Worker {}: Starting task id: {}'.format(worker_number, func.task_id), 'yellow'))
                try:
                    result = func(self.settings, *args, **kwargs)
                    self.collector_socket.send_pyobj((task_id, result))
                    print(colored('Worker {}: Task #{} finished'.format(worker_number, func.task_id), 'yellow'))
                except:
                    traceback.print_exc()
                    print(colored('Worker {}: Task #{} Error'.format(worker_number, func.task_id), 'yellow'))
            except KeyboardInterrupt:
                self.go = False


class QueueDevice(Device):

    def __init__(self, settings):
        super().__init__(settings)
        # self.frontend, self.backend = self.get_sockets()

    def get_sockets(self):
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.XREP)
        frontend.bind(self.settings.get('proxy.broker'))
        # Socket facing services
        backend = context.socket(zmq.XREQ)
        backend.bind(self.settings.get('proxy.worker_socket'))
        return frontend, backend

    def run(self):
        try:
            self.frontend, self.backend = self.get_sockets()
            zmq.device(zmq.QUEUE, self.frontend, self.backend)
        except KeyboardInterrupt:
            pass


class CollectorDevice(Device):

    def __init__(self, settings):
        super().__init__(settings)
        cache_manager = CacheManager(**parse_cache_config_options(self.settings))
        self.cache = cache_manager.get_cache_region('result_cache', 'result')
        global_registry.result_cache = self.cache

    def get_socket(self):
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.bind(self.settings.get('proxy.collector_socket'))
        return socket

    def run(self):
        socket = self.get_socket()
        while self.go:
            try:
                data = socket.recv()
                task_id, value = pickle.loads(data)
                self.cache.set_value(task_id, value)
            except KeyboardInterrupt:
                self.go = False
