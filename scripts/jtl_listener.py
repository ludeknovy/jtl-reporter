from datetime import datetime
from time import sleep, time
from pathlib import Path


class JtlListener:

    # holds results until processed
    csv_results = []
    master_csv_data = None
    results_file = None
    filename = None

    def __init__(
        self,
        env,
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

        # fields set by default in jmeter
        self.csv_headers = [
            "timeStamp",
            "elapsed",
            "label",
            "responseCode",
            "responseMessage",
            "dataType",
            "success",
            "failureMessage",
            "bytes",
            "sentBytes",
            "grpThreads",
            "allThreads",
            "Latency",
            "IdleTime",
            "Connect",
        ]
        self.user_count = 0
        self.testplan = ""
        events = self.env.events
        events.request_success.add_listener(self._request_success)
        events.request_failure.add_listener(self._request_failure)

        events.worker_report.add_listener(self._worker_report)
        events.report_to_master.add_listener(self._report_to_master)
        events.test_start.add_listener(self._test_start)
        events.test_stop.add_listener(self._test_stop)

    def _test_start(self, *a, **kw):
        self._create_results_log()

    def _report_to_master(self, client_id, data):
        data['csv'] = self.csv_results
        self.csv_results = []

    def _worker_report(self, client_id, data):
        if 'csv' in data:
            self.master_csv_data = data['csv']

        if self.master_csv_data and len(self.master_csv_data) > 0:
            self._flush_to_log()

    def _create_results_log(self):
        self.filename = "results_" + datetime.fromtimestamp(time()).strftime(self.results_timestamp_format) + ".csv"
        Path("logs/").mkdir(parents=True, exist_ok=True)
        results_file = open('logs/' + self.filename, "w")
        results_file.write(self.field_delimiter.join(self.csv_headers) + self.row_delimiter)
        results_file.flush()
        self.results_file = results_file

    def _flush_to_log(self):
        if self.results_file is None:
            return
        self.results_file.write(self.row_delimiter.join(self.master_csv_data) + self.row_delimiter)
        self.results_file.flush()
        self.master_csv_data = []

    def _test_stop(self, *a, **kw):
        sleep(5)  # wait for last reports to arrive
        if self.results_file:
            self.results_file.write(self.row_delimiter.join(self.master_csv_data) + self.row_delimiter)
            self.results_file.close()
            self.results_file = None


    def add_result(self, success, _request_type, name, response_time, response_length, exception, **kw):
        timestamp = str(int(round(time() * 1000)))
        response_message = "OK" if success == "true" else "KO"
        # check to see if the additional fields have been populated. If not, set to a default value
        status_code = kw["status_code"] if "status_code" in kw else "0"
        data_type = kw["data_type"] if "data_type" in kw else "unknown"
        bytes_sent = kw["bytes_sent"] if "bytes_sent" in kw else "0"
        group_threads = str(self.runner.user_count)
        all_threads = str(self.runner.user_count)
        latency = kw["latency"] if "latency" in kw else "0"
        idle_time = kw["idle_time"] if "idle_time" in kw else "0"
        connect = kw["connect"] if "connect" in kw else "0"

        row = [
            timestamp,
            str(round(response_time)),
            name,
            str(status_code),
            response_message,
            data_type,
            success,
            exception,
            str(response_length),
            bytes_sent,
            str(group_threads),
            str(all_threads),
            latency,
            idle_time,
            connect,
        ]
        self.csv_results.append(self.field_delimiter.join(row))

    def _request_success(self, request_type, name, response_time, response_length, **kw):
        self.add_result("true", request_type, name, response_time, response_length, "", **kw)

    def _request_failure(self, request_type, name, response_time, response_length, exception, **kw):
        self.add_result("false", request_type, name, response_time, response_length, str(exception), **kw)