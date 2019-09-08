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

## Taurus integration
Jtl Reporter can be easily integrated with Taurus. To do it we are going to use [shell exec module](https://gettaurus.org/docs/ShellExec/) and custom python upload script. Here is an example of test yaml configuration:
```
settings:
  env:
    BASE_URL: yourBaseUrl.com
    SCENARIO: demoScenario
    PROJECT: demoProject
execution:
  concurrency: 50
  ramp-up: 3m
  hold-for: 30m
  scenario: demoScenario

scenarios:
  demoScenario:
    script: jmx/demo.jmx
    variables:
      baseUrl: ${BASE_URL}

services:
 - module: shellexec
   post-process:
   - python $PWD/helper/upload_jtl.py -p ${PROJECT} -s ${SCENARIO} -e ${BASE_URL} -ec $TAURUS_EXIT_CODE -er "${TAURUS_STOPPING_REASON:-''}"
```
Do not forget to copy [upload_jtl.py](/scripts/upload_jtl.py) script into your project folder.

Please note that "demoProject" and "demoScenario" have to exist in Jtl Reporter beforehand otherwise it will return an error.

## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)


## Screenshot
![Item detail](/screenshots/item_detail.jpeg)

## License
Jtl Reporter is [GPL-3.0 licensed.](LICENSE)  
