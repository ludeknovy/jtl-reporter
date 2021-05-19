<h1 align="center">JtlReporter</h1>

![jtl gif](/assets/jtl.gif)

## Description
Online reporting application to generate reports from JMeter(Taurus), Locust and other tools by either uploading JTL(csv) file or streaming data from the test run continuously. JtlReporter's main objective is to help you to understand your performance reports better and to spot performance regression.

## Features
* Detailed performance report
* Test run comparison
* Performance regression alerts
* Performance insights
* [and more](https://jtlreporter.site/docs/introduction/features).

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
For additional information please refer to the [documentation](https://jtlreporter.site/docs/).

## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)
  * [listener](https://github.com/ludeknovy/jtl-reporter-listener-service)
  * [docs](https://github.com/ludeknovy/jtl-reporter-docs)


## Screenshot
![Item detail](/assets/item_detail.png)

## License
Jtl Reporter is GNU Affero General Public License v3.0 licensed ([frontend](https://github.com/ludeknovy/jtl-reporter-fe/blob/master/LICENSE), [backend](https://github.com/ludeknovy/jtl-reporter-be/blob/master/LICENSE) and [listener](https://github.com/ludeknovy/jtl-reporter-listener-service/blob/main/LICENSE)). 

This repository is [MIT licensed.](LICENSE)
