## Description
 Reporting tool for [Taurus](https://gettaurus.org)(JMeter) load tests. Jtl Reporter is meant to be used as addition to Grafana perf stack. While Grafana provides great solution for live data preview it falls short of easy test run retrospective. Jtl Reporter's main objective is to give you the possibility compare test runs with ease.

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

## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)


## Screenshot
![Item detail](/screenshots/item_detail.jpeg)

## License
Jtl Reporter is [GPL-3.0 licensed.](LICENSE)  
