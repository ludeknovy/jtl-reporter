import logging
import os
import sys
from time import sleep, time
from typing import List, Optional, Dict, Any, Union

import gevent
from gevent import Greenlet
import requests
from locust.env import Environment
from locust.runners import WorkerRunner
from locust.clients import LocustResponse
from locust.contrib.fasthttp import FastResponse


class JtlListener:

    """
    JTL Reporter integration for Locust.
    
    IMPORTANT: Remember to customize the get_test_status() method 
    to implement your test success criteria.
    """

    def __init__(
            self,
            env: Environment,
            project_name: str,
            scenario_name: str,
            backend_url: str,
            environment_name: Optional[str] = None,
    ):
        
        # Validate critical parameters
        if not project_name or not scenario_name:
            raise ValueError("project_name and scenario_name are required")
        if not backend_url:
            raise ValueError("backend_url is required")
        if "JTL_API_TOKEN" not in os.environ:
            raise ValueError("JTL_API_TOKEN environment variable is required")

        # Listener configuration
        self.flush_size: int = 500  # how many records should be held before flushing to reporter
        #
        
        # Advanced parameters
        self._batch_size_multiplier: int = 1  # base multiplier for batch size (flush_size * 1)
        self._batch_size_multiplier_growth_threshold: int = 4  # threshold for growing the batch size multiplier (batch_size * 4)
        # 
        
        # Initialize batch_size_multiplier
        self._current_batch_size_multiplier = self._batch_size_multiplier

        self.env = env
        self.environment_name = environment_name or self.env.host
        self.runner = self.env.runner
        self.project_name = project_name
        self.scenario_name = scenario_name
        self.backend_url = backend_url
        self.api_token: str = os.environ["JTL_API_TOKEN"]
        self.be_url: str = f"{self.backend_url}:5000"
        self.listener_url: str = f"{self.backend_url}:6000"

        self.user_count: int = 0
        self.results: List[Dict[str, Any]] = []
        self.cpu_usage: List[Dict[str, Any]] = []
        self.jwt_token: Optional[str] = None
        self.item_id: Optional[str] = None
        self._senders: List[Greenlet] = []

        # Internal flag used to indicate that the Locust test has ended
        self._finished: bool = False
        
        # Background task greenlets
        self._background_processor: Optional[Greenlet] = None
        self._background_master_monitor: Optional[Greenlet] = None
        self._background_user: Optional[Greenlet] = None
        self._background_status_monitor: Optional[Greenlet] = None

        events = self.env.events
        events.request.add_listener(self._request)
        events.worker_report.add_listener(self._worker_report)
        events.report_to_master.add_listener(self._report_to_master)
        events.test_start.add_listener(self._test_start)
        events.test_stop.add_listener(self._test_stop)

        # Initialize dynamic values for current batch size and current growth threshold
        self._set_dynamic_values()

    def get_test_status(self) -> int:
        """Get test status code.
        
        Users should customize this method to implement their own test success criteria.
        
        Available status codes:
        * 0 for Passed
        * 1 for Error  
        * 2 for Terminated
        * 3 for Failed
        * 10 for Not Set
        
        Returns:
            int: Status code based on test performance metrics.
        """
        # TODO: Implement your test success criteria here
        # Examples:
        # - Check if self.runner.stats.total.avg_response_time > threshold
        # - Check if self.runner.stats.total.fail_ratio > error_threshold
        # - Check specific endpoints: self.runner.stats.entries[endpoint_name]
        
        # Example implementation:
        # if self.runner.stats.total.fail_ratio > 0.05:  # 5% error rate
        #     return 3  # Failed
        # return 0  # Passed
        
        return 0  # Default: Passed

    # === CONFIGURATION AND SETUP METHODS ===
    def _set_dynamic_values(self) -> None:
        """Update dynamic batch size and growth threshold values."""
        if not self._is_worker():
            self._current_batch_size = self.flush_size * self._current_batch_size_multiplier
            self._current_growth_threshold = self._current_batch_size * self._batch_size_multiplier_growth_threshold
            logging.debug(f"JtlListener: dynamic values set to batch_size: {self._current_batch_size} and growth_threshold: {self._current_growth_threshold}")

    def _calculate_batch_size(self, backlog_size: int) -> int:
        """
        Calculate dynamic batch size based on backlog.
        Adjusts the batch multiplier if the backlog exceeds the growth threshold.
        """
        # Check if the batch size multiplier needs to be increased
        if backlog_size >= self._current_growth_threshold:
            self._current_batch_size_multiplier += 1
            self._set_dynamic_values()  # Recalculate dynamic values only when multiplier changes

        return self._current_batch_size

    # === AUTHENTICATION AND API METHODS ===
    def _login(self) -> str:
        logging.info("JtlListener: Logging with token")
        try:
            payload: Dict[str, str] = {
                "token": self.api_token
            }
            response = requests.post(
                f"{self.be_url}/api/auth/login-with-token", json=payload)
            logging.info(f"JtlListener: Login with token returned {response.json()}")
            return response.json()["jwtToken"]
        except Exception:
            logging.error("JtlListener: Unable to get token")
            raise Exception

    def _start_test_run(self) -> Dict[str, Any]:
        logging.info("JtlListener: Starting async item in Reporter")
        try:
            headers: Dict[str, str] = {
                "x-access-token": self.api_token
            }
            payload: Dict[str, Any] = {
                "environment": self.environment_name
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/start-async",
                json=payload, headers=headers)
            logging.info(f"JtlListener: Reporter responded with {response.json()}")
            return response.json()
        except Exception:
            logging.error("Starting async item in Reporter failed")
            raise Exception

    def _stop_test_run(self) -> None:
        try:
            # If you want to set the status, please check: https://jtlreporter.site/docs/integrations/samples-streaming#4-stop-the-test-run
            headers: Dict[str, str] = {
                "x-access-token": self.api_token
            }
            payload = {
                "status": str(self.get_test_status())
            }
            response = requests.post(
                f"{self.be_url}/api/projects/{self.project_name}/scenarios/{self.scenario_name}/items/{self.item_id}/stop-async",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            logging.info("JtlListener: Test run stopped successfully")
        except Exception:
            logging.error("JtlListener: Stopping test run has failed")
            raise Exception

    # === DATA PROCESSING AND RESULTS METHODS ===
    def _add_result(self, 
                   _request_type: str, 
                   name: str, 
                   response_time: float, 
                   response_length: int, 
                   response: Union[LocustResponse, FastResponse], 
                   context: Any, 
                   exception: Optional[Exception]) -> None:
        timestamp = int(round(time() * 1000))
        response_message = str(response.reason) if "reason" in dir(response) else ""
        status_code = response.status_code
        group_threads = str(self.runner.user_count)
        all_threads = str(self.runner.user_count)
        latency = 0
        connect = 0

        result: Dict[str, Any] = {
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

    def _process_batch(self) -> None:
        """
        Processing greenlet that handles batches of results with dynamic sizing
        """
        logging.info("JtlListener: Starting batch processor")
        
        while True:
            if self._finished and len(self.results) == 0:
                logging.debug("JtlListener: Batch processor found no more results")
                break
                
            if not self.item_id:
                gevent.sleep(0.1)
                continue
                
            # Get current backlog size
            backlog_size = len(self.results)

            # Calculate dynamic group size
            batch_size = self._calculate_batch_size(backlog_size)
            
            # Get batch of results to process
            results_batch: List[Dict[str, Any]] = []
            if len(self.results) >= batch_size:
                results_batch = self.results[:batch_size]
                del self.results[:batch_size]
            elif self._finished and len(self.results) > 0:
                results_batch = self.results[:]
                self.results.clear()
                    
            # Process CPU usage with same logic
            cpu_usage_batch: List[Dict[str, Any]] = []
            if len(self.cpu_usage) >= batch_size:
                cpu_usage_batch = self.cpu_usage[:batch_size]
                del self.cpu_usage[:batch_size]
            elif self._finished and len(self.cpu_usage) > 0:
                cpu_usage_batch = self.cpu_usage[:]
                self.cpu_usage.clear()

            # Process the batch if we have data
            if results_batch:
                logging.debug(f"JtlListener: Processing {len(results_batch)} results entries")
                
                # Clean up dead senders
                self._senders = [sender for sender in self._senders if not sender.dead]
                
                # Spawn new sender
                self._senders.append(gevent.spawn(self._log_results, results_batch, cpu_usage_batch))
                logging.debug(f"JtlListener: {len(self._senders)} senders in flight")

            gevent.sleep(0.05)
        
        logging.info("JtlListener: Batch processor terminated")

    def _log_results(self, results_batch: List[Dict[str, Any]], cpu_usage_batch: List[Dict[str, Any]]) -> None:
        while True:
            try:
                results = results_batch[:self.flush_size]
                cpu_usage = cpu_usage_batch[:self.flush_size]
                del results_batch[:self.flush_size]
                del cpu_usage_batch[:self.flush_size]

                if len(results) == 0:
                    logging.debug("JtlListener: Sender found no further results.")
                    break

                logging.debug(f"JtlListener: sending asynchronously {len(results)} results")
                payload: Dict[str, Any] = {
                    "itemId": self.item_id,
                    "samples": results,
                    "monitor": cpu_usage,
                }
                headers: Dict[str, str] = {
                    "x-access-token": self.jwt_token
                }
                requests.post(
                    f"{self.listener_url}/api/v4/test-run/log-samples",
                    json=payload, headers=headers
                )
            except Exception:
                logging.error("JtlListener: Logging results failed")
                raise Exception
            
            gevent.sleep(0.05)
        
        logging.debug("JtlListener: The sender has finished.")

    # === MONITORING AND SYSTEM METHODS ===
    def _master_cpu_monitor(self) -> None:
        while True:
            self.cpu_usage.append({
                "name": "master",
                "cpu": self._get_cpu(),
                "mem": self._get_memory_usage(),
                "timestamp": int(round(time() * 1000))
            })
            if self._finished:
                break
            gevent.sleep(5)

    def _user_count(self) -> None:
        while True:
            self.user_count = self.runner.user_count
            if self._finished:
                break
            gevent.sleep(3)

    def _get_cpu(self) -> float:
        return self.runner.current_cpu_usage

    def _get_memory_usage(self) -> float:
        return self.runner.current_memory_usage

    # === LOCUST EVENT HANDLERS ===
    def _request(self, 
                 request_type: str, 
                 name: str, 
                 response_time: float, 
                 response_length: int, 
                 response: Union[LocustResponse, FastResponse], 
                 context: Any, 
                 exception: Optional[Exception], 
                 **kw) -> None:
        self._add_result(request_type, name,
                        response_time, response_length, response, context, exception)

    def _test_start(self, *a, **kw) -> None:
        if not self._is_worker():
            try:
                self.jwt_token = self._login()
                response = self._start_test_run()
                self.item_id = response["itemId"]

                logging.info("JtlListener: Setting up background tasks")
                self._finished = False
                
                # Reset dynamic parameters
                self._current_batch_size_multiplier = self._batch_size_multiplier
                
                self._background_processor = gevent.spawn(self._process_batch)
                self._background_master_monitor = gevent.spawn(self._master_cpu_monitor)
                self._background_user = gevent.spawn(self._user_count)

            except Exception:
                logging.error("Error while starting the test")
                sys.exit(1)

    def _test_stop(self, *a, **kw) -> None:
        if not self._is_worker():
            sleep(10)  # wait for last reports to arrive
            logging.info(f"JtlListener: Test is stopping, number of remaining results to be uploaded yet: {len(self.results)}")
            
            self._finished = True
            
            # Wait for all greenlets to complete
            self._background_processor.join(timeout=60)
            self._background_user.join(timeout=5)
            self._background_master_monitor.join(timeout=None)
            if self._senders:
                logging.info(f"JtlListener: Waiting for {len(self._senders)} senders to complete")
                gevent.joinall(self._senders, timeout=60)
            
            logging.info(f"JtlListener: Number of results not uploaded: {len(self.results)}")
            self._stop_test_run()

    # === WORKER/MASTER COMMUNICATION METHODS ===
    def _report_to_master(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle report to master event (worker side)."""
        data["results"] = self.results[:]
        self.results.clear()
        data["cpu_usage"] = {
            "name": client_id, 
            "timestamp": int(round(time() * 1000)), 
            "cpu": self._get_cpu(), 
            "mem": self._get_memory_usage()
        }

    def _worker_report(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle report from worker event (master side)."""
        if 'results' in data:
            for result in data['results']:
                result["allThreads"] = self.user_count
            self.results.extend(data['results'])
        
        if 'cpu_usage' in data:
            self.cpu_usage.append(data["cpu_usage"])

    # === UTILITY METHODS ===
    def _is_worker(self) -> bool:
        return isinstance(self.runner, WorkerRunner)