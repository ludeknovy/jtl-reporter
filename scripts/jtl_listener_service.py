import gevent
import gevent.monkey
import socket

from time import sleep, time
import requests
import logging
from typing import List
import sys
import os


class JtlListener:
    # holds results until processed
    results: List[dict] = []

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
        # how many records should be held before flushing to disk
        self.flush_size = 500
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

    def _run(self):
        while True:
            if self.item_id and len(self.results) >= self.flush_size:
                results_to_log = self.results[:self.flush_size]
                cpu_usage_to_log = self.cpu_usage[:self.flush_size]
                del self.results[:self.flush_size]
                del self.cpu_usage[:self.flush_size]
                self._log_results(results_to_log, cpu_usage_to_log)
            else:
                if self._finished:
                    results_len = len(self.results)
                    cpu_usage_len = len(self.cpu_usage)
                    self._log_results(self.results, self.cpu_usage)
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

    def _log_results(self, results, cpu_usage):
        try:
            payload = {
                "itemId": self.item_id,
                "samples": results,
                "monitor": cpu_usage,

            }
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
            headers = {
                "x-access-token": self.api_token
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/{self.item_id}/stop-async",
                headers=headers)
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
                self._background = gevent.spawn(self._run)
                self._background_master_monitor = gevent.spawn(self._master_cpu_monitor)
                self._background_user = gevent.spawn(self._user_count)
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
            logging.info(
                f"Test is stopping, number of remaining results to be uploaded yet: {len(self.results)}")
            self._finished = True
            self._background.join(timeout=5)
            self._background_user.join(timeout=5)
            self._background_master_monitor.join(timeout=None)
            logging.info(f"Number of results not uploaded {len(self.results)}")
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

