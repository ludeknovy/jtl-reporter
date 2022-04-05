from datetime import datetime
from time import time, sleep
from pathlib import Path
from locust.runners import WorkerRunner
import os, sys
import requests
import socket


class JtlListener:
    # holds results until processed
    csv_results = []
    results_file = None
    filename = None

    def __init__(
            self,
            env,
            project_name: str,
            scenario_name: str,
            environment: str,
            backend_url: str,
            field_delimiter=",",
            row_delimiter="\n",
            timestamp_format="%Y-%m-%d %H:%M:%S",
            flush_size=100,
    ):
        self.env = env
        self.runner = self.env.runner
        # default JMeter field and row delimiters
        self.field_delimiter = field_delimiter
        self.row_delimiter = row_delimiter
        # a timestamp format, others could be added...
        self.timestamp_format = timestamp_format
        # how many records should be held before flushing to disk
        self.flush_size = flush_size
        # results filename format
        self.results_timestamp_format = "%Y_%m_%d_%H_%M_%S"
        self._worker_id = f"{socket.gethostname()}_{os.getpid()}"
        self.is_worker_runner = isinstance(self.env.runner, WorkerRunner)


        self.api_token = os.environ["JTL_API_TOKEN"]
        self.project_name = project_name
        self.scenario_name = scenario_name
        self.environment = environment
        self.backend_url = backend_url

        # fields set by default in jmeter
        self.csv_headers = [
            "timeStamp",
            "elapsed",
            "label",
            "responseCode",
            "responseMessage",
            "dataType",
            "success",
            "bytes",
            "sentBytes",
            "grpThreads",
            "allThreads",
            "Latency",
            "IdleTime",
            "Connect",
            "Hostname",
            "failureMessage"
        ]
        self.user_count = 0
        events = self.env.events
        events.request.add_listener(self._request)
        if self.is_worker():
            events.report_to_master.add_listener(self._report_to_master)
        else:
            events.test_start.add_listener(self._test_start)
            events.test_stop.add_listener(self._test_stop)
            events.worker_report.add_listener(self._worker_report)

    def _test_start(self, *a, **kw):
        self._create_results_log()

    def _report_to_master(self, client_id, data):
        data['csv'] = self.csv_results
        self.csv_results = []

    def _worker_report(self, client_id, data):
        self.csv_results += data["csv"]
        if len(self.csv_results) >= self.flush_size:
            self._flush_to_log()

    def _create_results_log(self):
        self.filename = "results_" + \
                        datetime.fromtimestamp(time()).strftime(
                            self.results_timestamp_format) + ".csv"
        Path("logs/").mkdir(parents=True, exist_ok=True)
        results_file = open('logs/' + self.filename, "w")
        results_file.write(self.field_delimiter.join(
            self.csv_headers) + self.row_delimiter)
        results_file.flush()
        self.results_file = results_file

    def _flush_to_log(self):
        if self.results_file is None:
            return
        self.results_file.write(self.row_delimiter.join(
            self.csv_results) + self.row_delimiter)
        self.results_file.flush()
        self.csv_results = []

    def _test_stop(self, *a, environment):
        # wait for last reports to arrive
        sleep(5)
        # final writing a data and clearing self.csv_results between restarts
        if not self.is_worker():
            self._flush_to_log()
        if self.results_file:
            self.results_file.write(self.row_delimiter.join(
                self.csv_results) + self.row_delimiter)
        if self.project_name and self.scenario_name and self.api_token and self.environment:
            try:
                self._upload_file()
            except Exception as e:
                print(e)

    def _upload_file(self):
        files = dict(
            kpi=open('logs/' + self.filename, 'rb'),
            environment=(None, self.environment),
            status=(None, 1))
        url = '%s:5000/api/projects/%s/scenarios/%s/items' % (
            self.backend_url, self.project_name, self.scenario_name)
        response = requests.post(url, files=files, headers={
            'x-access-token': self.api_token})
        if response.status_code != 200:
            raise Exception("Upload failed: %s" % response.text)

    def add_result(self, _request_type, name, response_time, response_length, response, context, exception, **kw):
        timestamp = str(int(round(time() * 1000)))
        response_message = str(response.reason) if "reason" in dir(response) else ""
        status_code = response.status_code
        success = "false" if exception else "true"
        # check to see if the additional fields have been populated. If not, set to a default value
        data_type = kw["data_type"] if "data_type" in kw else "unknown"
        bytes_sent = kw["bytes_sent"] if "bytes_sent" in kw else "0"
        group_threads = str(self.runner.user_count)
        all_threads = str(self.runner.user_count)
        latency = kw["latency"] if "latency" in kw else "0"
        idle_time = kw["idle_time"] if "idle_time" in kw else "0"
        connect = kw["connect"] if "connect" in kw else "0"
        hostname = self._worker_id

        row = [
            timestamp,
            str(round(response_time)),
            name,
            str(status_code),
            response_message,
            data_type,
            success,
            str(response_length),
            bytes_sent,
            str(group_threads),
            str(all_threads),
            latency,
            idle_time,
            connect,
            hostname,
            str(exception)
        ]
        # Safe way to generate csv row up to RFC4180
        # https://datatracker.ietf.org/doc/html/rfc4180
        # It encloses all fields in double quotes and escape single double-quotes chars with double double quotes.
        # Example: " -> ""
        csv_row_str = self.field_delimiter.join(['"' + x.replace('"', '""') + '"' for x in row])
        self.csv_results.append(csv_row_str)
        if len(self.csv_results) >= self.flush_size and not self.is_worker():
            self._flush_to_log()

    def _request(self, request_type, name, response_time, response_length, response, context, exception, **kw):
        self.add_result(request_type, name,
                        response_time, response_length, response, context, exception)

    def is_worker(self):
        return "--worker" in sys.argv
