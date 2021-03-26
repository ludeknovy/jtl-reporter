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
        print(env.host)
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
        self.jwt_token = None

        events = self.env.events
        events.request_success.add_listener(self._request_success)
        events.request_failure.add_listener(self._request_failure)

        events.worker_report.add_listener(self._worker_report)
        events.report_to_master.add_listener(self._report_to_master)
        events.test_start.add_listener(self._test_start)
        events.test_stop.add_listener(self._test_stop)

    def _run(self):
        while True:
            if len(self.results) >= self.flush_size:
                results_to_log = self.results[:self.flush_size]
                del self.results[:self.flush_size]
                self._log_results(results_to_log)
            else:
                if self._finished:
                    results_len = len(self.results)
                    self._log_results(self.results)
                    del self.results[:results_len]
                    break
            gevent.sleep(0.05)

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
            logging.error(Exception)
            raise Exception

    def _log_results(self, results):
        try:
            payload = {
                "dataId": self.data_id,
                "samples": results
            }
            headers = {
                "x-access-token": self.jwt_token
            }
            requests.post(
                f"{self.listener_url}/api/v1/test-run/log-samples", json=payload, headers=headers)

        except Exception:
            logging.error("Unable to to get token")
            raise Exception

    def _stop_test_run(self):
        try:
            headers = {
                "x-access-token": self.api_token
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/{self.item_id}/stop-async",
                headers=headers)
            return response.json()
        except Exception:
            logging.error(Exception)
            raise Exception

    def _test_start(self, *a, **kw):
        if self._is_master():
            self.jwt_token = self._login()
            logging.info("Setting up background tasks")
            self._finished = False
            self._background = gevent.spawn(self._run)
            self._background_user = gevent.spawn(self._user_count)

        response = self._start_test_run()
        self.data_id = response["dataId"]
        self.item_id = response["itemId"]

    def _report_to_master(self, client_id, data):
        data["results"] = self.results
        self.results = []

    def _worker_report(self, client_id, data):
        if 'results' in data:
            for result in data['results']:
                result["allThreads"] = self.user_count
            self.results += data['results']

    def _test_stop(self, *a, **kw):
        sleep(5)  # wait for last reports to arrive
        logging.info(
            f"Test is stopping, number of remaining results to be uploaded yet: {len(self.results)}")
        self._finished = True
        self._background.join(timeout=None)
        self._background_user.join(timeout=None)
        logging.info(f"Results :::::: {len(self.results)}")
        self._stop_test_run()

    def add_result(self, success, _request_type, name, response_time, response_length, exception, **kw):
        timestamp = str(int(round(time() * 1000)))
        response_message = "OK" if success == "true" else "KO"
        status_code = kw["status_code"] if "status_code" in kw else "0"
        group_threads = str(self.runner.user_count)
        all_threads = str(self.runner.user_count)
        latency = kw["latency"] if "latency" in kw else 0
        connect = kw["connect"] if "connect" in kw else 0

        result = {
            "timeStamp": timestamp,
            "elapsed": str(round(response_time)),
            "label": name,
            "responseCode": str(status_code),
            "responseMessage": response_message,
            "success": success,
            "failureMessage": exception,
            "bytes": str(response_length),
            "grpThreads": str(group_threads),
            "allThreads": str(all_threads),
            "Latency": latency,
            "Connect": connect,
        }
        self.results.append(result)

    def _request_success(self, request_type, name, response_time, response_length, **kw):
        self.add_result("true", request_type, name,
                        response_time, response_length, "", **kw)

    def _request_failure(self, request_type, name, response_time, response_length, exception, **kw):
        self.add_result("false", request_type, name, response_time,
                        response_length, str(exception), **kw)

    def _is_master(self):
        return "--master" in sys.argv
