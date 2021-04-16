<h1 align="center">JtlReporter</h1>

![jtl gif](/assets/jtl.gif)

## Description
Online reporting application to generate reports from JMeter(Taurus), Locust and other tools by either uploading JTL(csv) file or streaming data from the test run continuously. JtlReporter's main objective is to help you to understand your performance reports better and to spot performance regression.

## Features
#### Detailed performance report
JtlReport will provide you with metrics for each label (endpoint call) such as requests per seconds, various percentiles, error rate and more. It will provide you the overall stats as well, eg: the total throughput (RPS), 90% percentile, network data transferred (mbps). Besides the prepared charts (throughput, response times, network, and so on), you can create your custom chart from the available metrics to further explore the performance report.

#### Test run comparison
If you want to compare HTML reports, you need to open them side by side and look for the differences and correlations on your own. With JtlReporter that comparison is only four clicks away. And it does not stop there. You can even drill down in response time and throughput trends for each label (endpoint call).

#### Performance regression alerts
If you run your performance tests regularly as a part of your delivery pipeline, you might set up performance thresholds for response time, error rate, and throughput. With each new report processing, it checks the long-term averages for the same environment. In case the performance did degrade above set up thresholds, you will get an alert in the report detail.

#### Performance insights
JtlReport will perform some performance analysis automatically for you. It aims to help you to interpret the outcome of the measurements and warn you if there might be an issue related to an overloaded system under tests. Currently, the application checks three metrics, and if any of them evinces poor performance it will get marked with detailed information.

## Installation steps
1. Install [Docker](https://docs.docker.com/engine/installation/) ([Engine](https://docs.docker.com/engine/installation/), [Compose](https://docs.docker.com/compose/install/))
2. Clone this repository and navigate into cloned folder
3. Deploy JtlReporter using `docker-compose` within the same folder

  ```Shell
  $ docker-compose up -d
  ```

4. Open in your browser IP address of deployed environment at port `2020`

  ```
  $ http://IP_ADDRESS:2020
  ```

5. Default credentials

  ```
  username: admin
  password: 2Txnf5prDknTFYTVEXjj
  ```
  
## Documentation 📖
For additional information please refer to [documentation](https://jtlreporter.site).

## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)
  * [listener](https://github.com/ludeknovy/jtl-reporter-listener-service)
  * [docs](https://github.com/ludeknovy/jtl-reporter-docs)


## Screenshot
![Item detail](/assets/item_detail.png)

## License
Jtl Reporter is [GPL-3.0 licensed.](LICENSE)  
