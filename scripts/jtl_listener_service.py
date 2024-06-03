from time import sleep, time
from typing import List
from gevent.queue import Queue
import gevent, gevent.monkey, os, sys, logging, requests, socket


class JtlListener:
    # holds results until processed
    results: List[dict] = []

    # holds cpu metrics until processed
    cpu_usage = []

    # Queue procesors
    _background_senders = []
    _background_receivers = []

    # Queues
    payloads = Queue()
    results_queue = Queue()
    cpu_usage_queue = Queue()

    def __init__(
            self,
            env,
            project_name: str,
            scenario_name: str,
            backend_url: str,
            hostname: str = socket.gethostname(),
            timestamp_format="%Y-%m-%d %H:%M:%S",
    ):
        self.env = env
        self.runner = self.env.runner
        self.project_name = project_name
        self.scenario_name = scenario_name
        self.hostname = hostname
        self.backend_url = backend_url
        self.api_token = os.environ["JTL_API_TOKEN"]
        self.be_url = f"{self.backend_url}:5000"
        self.listener_url = f"{self.backend_url}:6000"

        # a timestamp format, others could be added...
        self.timestamp_format = timestamp_format
        
        # how many records will be sent at once?
        self.flush_size = 500

        # how many senders threads can it have at most?
        self.senders_max_threads = 30

        # how many receivers threads can it have at most?
        self.receivers_max_threads = 30

        # how often will the senders threads send in seconds?
        self.senders_interval = 1

        # how often will the receivers threads send in seconds?
        self.receivers_interval = 1

        # how many times will the "flush_size" be collected to queue results?
        # he higher the multiplier, the ability to receive results increases.
        # x3 is tested at up to 20,000 TPS
        self.enqueue_grouping = 3

        # results filename format
        self.results_timestamp_format = "%Y_%m_%d_%H_%M_%S"
        self._finished = False
        self.user_count = 0
        self.cpu_usage = []
        self.jwt_token = None

        events = self.env.events
        events.request.add_listener(self._request)
        events.worker_report.add_listener(self._worker_report)
        events.report_to_master.add_listener(self._report_to_master)
        events.test_start.add_listener(self._test_start)
        events.test_stop.add_listener(self._test_stop)

    def _send(self, name):
        # concurrent greenlets will use this method to take queued payloads and send them to jtl-reporter-listener.
        while True:
            gevent.sleep(self.senders_interval)
            try:
                self._log_results(payload=self.payloads.get(timeout=10))
            except:
                if self._finished:
                    logging.info(f"Stoping jtl-reporter {name}")
                    break

    def _receive(self, name):
        # concurrent greenlets will use this method to take the enqueued results and enqueue them as sendable payloads
        while True:
            gevent.sleep(self.receivers_interval)
            try:
                results = self.results_queue.get(timeout=10)
                try:
                    cpu_usage = self.cpu_usage_queue.get(timeout=10)
                except:
                    cpu_usage=[]

                while True:
                    if len(results) > 0:
                        results_to_log = results[:self.flush_size]
                        cpu_usage_to_log = cpu_usage[:self.flush_size]
                        del results[:self.flush_size]
                        del cpu_usage[:self.flush_size]
                        self.payloads.put_nowait({
                            "itemId": self.item_id,
                            "samples": results_to_log,
                            "monitor": cpu_usage_to_log,
                        })
                    else:
                        break
                    gevent.sleep(0.05)
            except:
                if self._finished:
                    logging.info(f"Stoping jtl-reporter {name}")
                    break

    def _senders_manage(self):
        # this method for a greenlet running in the background increases the number of threads preventing the payloads queue from growing
        logging.info(f"Starting jtl-reporter sender manager")
        while True:
            gevent.sleep(1)
            len_senders = len(self._background_senders)
            if self.payloads.qsize() > 10 or len_senders == 0:
                if len_senders < self.senders_max_threads:
                    name = f"sender {len_senders+1}"
                    logging.info(f"Starting jtl-reporter {name}")
                    self._background_senders.append(gevent.spawn(self._send,name))
                else:
                    logging.info(f"Senders limit (senders_max_threads={self.senders_max_threads}) reached.\n Payloads queue size: {self.payloads.qsize()}")
            if self._finished:
                logging.info(f"Stoping jtl-reporter sender manager")
                break
    
    def _receivers_manage(self):
        # this method for a greenlet running in the background increases the number of threads preventing the results queue from growing
        logging.info(f"Starting jtl-reporter receiver manager")
        while True:
            gevent.sleep(1)
            len_receivers = len(self._background_receivers)
            if self.results_queue.qsize() > 10 or len_receivers == 0:
                if len_receivers < self.receivers_max_threads:
                    name = f"receiver {len_receivers+1}"
                    logging.info(f"Starting jtl-reporter {name}")
                    self._background_receivers.append(gevent.spawn(self._receive,name))
                else:
                    logging.info(f"Receivers limit (receivers_max_threads={self.receivers_max_threads}) reached.\n Results queue size: {self.results_queue.qsize()}")
            if self._finished:
                logging.info(f"Stoping jtl-reporter receiver manager")
                break
        
    def _enqueue(self):
        # this method for a greenlet background receives the results from the workers and queues them
        while True:
            # to increase receiving capacity, apply a flush_size multiplier.
            flush_size = self.flush_size * self.enqueue_grouping
            if self.item_id and len(self.results) >= flush_size:
                results_to_log = self.results[:flush_size]
                cpu_usage_to_log = self.cpu_usage[:flush_size]
                del self.results[:flush_size]
                del self.cpu_usage[:flush_size]
                self.results_queue.put_nowait(results_to_log)
                self.cpu_usage_queue.put_nowait(cpu_usage_to_log)
            else:
                if self._finished:
                    results_len = len(self.results)
                    cpu_usage_len = len(self.cpu_usage)
                    self.results_queue.put_nowait(self.results[:])
                    self.cpu_usage_queue.put_nowait(self.cpu_usage[:])
                    del self.results[:results_len]
                    del self.cpu_usage[:cpu_usage_len]
                    break
            gevent.sleep(0.05)

    def _master_cpu_monitor(self):
        while True:
            self.cpu_usage.append({ "name": "master", "cpu": self.get_cpu(), "timestamp": int(round(time() * 1000)) })
            if self._finished:
                break
            gevent.sleep(5)

    def _user_count(self):
        while True:
            self.user_count = self.runner.user_count
            if self._finished:
                break
            gevent.sleep(3)

    def _login(self):
        logging.info("Logging with token")
        try:
            payload = {
                "token": self.api_token
            }
            response = requests.post(
                f"{self.be_url}/api/auth/login-with-token", json=payload)
            logging.info(f"Login with token returned {response.json()}")
            return response.json()["jwtToken"]
        except Exception:
            logging.error("Unable to to get token")
            raise Exception

    def _start_test_run(self):
        logging.info("Starting async item in Reporter")
        try:
            headers = {
                "x-access-token": self.api_token
            }
            payload = {
                "environment": self.env.host
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/start-async",
                json=payload, headers=headers)
            logging.info(f"Reporter responded with {response.json()}")
            return response.json()
        except Exception:
            logging.error("Starting async item in Reporter failed")
            raise Exception

    def _log_results(self, payload):
        try:
            headers = {
                "x-access-token": self.jwt_token
            }
            response = requests.post(
                f"{self.listener_url}/api/v2/test-run/log-samples", json=payload, headers=headers)

        except Exception:
            logging.error("Logging results failed")
            raise Exception

    def _stop_test_run(self):
        try:
            ## If you want to set the status, please check: https://jtlreporter.site/docs/integrations/samples-streaming#4-stop-the-test-run
            headers = {
                "x-access-token": self.api_token
            }
            body = {
                "status": "0"
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/{self.item_id}/stop-async",
                headers=headers,
                json=body)
        except Exception:
            logging.error("Stopping test run has failed")
            raise Exception

    def _test_start(self, *a, **kw):
        if not self.is_worker():
            try:
                self.jwt_token = self._login()
                response = self._start_test_run()
                self.item_id = response["itemId"]

                logging.info("Setting up background tasks")
                self._finished = False
                self._background_enqueuer = gevent.spawn(self._enqueue)
                self._background_master_monitor = gevent.spawn(self._master_cpu_monitor)
                self._background_user = gevent.spawn(self._user_count)
                self._background_senders_manager = gevent.spawn(self._senders_manage)
                self._background_receivers_manager = gevent.spawn(self._receivers_manage)

                logging.info(response)
            except Exception:
                logging.error("Error while starting the test")
                sys.exit(1)

    def _report_to_master(self, client_id, data):
        data["results"] = self.results
        data["cpu_usage"] = {  "name": client_id, "timestamp": int(round(time() * 1000)) , "cpu": self.get_cpu() }
        self.results = []

    def _worker_report(self, client_id, data):
        if 'results' in data:
            for result in data['results']:
                result["allThreads"] = self.user_count
            self.results += data['results']
        if 'cpu_usage' in data:
            self.cpu_usage.append(data["cpu_usage"])

    def _test_stop(self, *a, **kw):
        if not self.is_worker():
            sleep(10)  # wait for last reports to arrive
            logging.info(f"Test is stopping")
            logging.info(f"Number of results yet to be enqueued: {len(self.results)}")
            logging.info(f"Number of results still enqueued: {self.results_queue.qsize()}")
            logging.info(f"Number of payloads yet to be sent: {self.payloads.qsize()}")
            self._finished = True
            self._background_user.join()
            self._background_master_monitor.join()
            self._background_enqueuer.join()
            gevent.joinall(self._background_receivers)
            gevent.joinall(self._background_senders)
            self._background_receivers_manager.join()
            self._background_senders_manager.join()
            self._background_receivers.clear()
            self._background_senders.clear()
            logging.info(f"Number of results not enqueued: {len(self.results)}")
            logging.info(f"Number of results in queue: {self.results_queue.qsize()}")
            logging.info(f"Number of payloads not sent: {self.payloads.qsize()}")
            self._stop_test_run()

    def add_result(self, _request_type, name, response_time, response_length, response, context, exception):
        timestamp = int(round(time() * 1000))
        response_message = str(response.reason) if "reason" in dir(response) else ""
        status_code = response.status_code
        group_threads = str(self.runner.user_count)
        all_threads = str(self.runner.user_count)
        latency = 0
        connect = 0

        result = {
            "timeStamp": timestamp,
            "elapsed": str(round(response_time)),
            "label": name,
            "responseCode": str(status_code),
            "responseMessage": response_message,
            "success": "false" if exception else "true",
            "failureMessage": str(exception),
            "bytes": str(response_length),
            "grpThreads": str(group_threads),
            "allThreads": str(all_threads),
            "latency": latency,
            "connect": connect,
        }
        self.results.append(result)

    def _request(self, request_type, name, response_time, response_length, response, context, exception, **kw):
        self.add_result(request_type, name,
                        response_time, response_length, response, context, exception)

    def is_worker(self):
        return "--worker" in sys.argv

    def get_cpu(self):
        return self.runner.current_cpu_usage