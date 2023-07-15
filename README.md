
<h1 align="center">JtlReporter</h1>

https://user-images.githubusercontent.com/13610612/126042981-41b48823-b715-423e-82ed-2bcb4b27334e.mov

## Description
Online reporting application to generate reports from JMeter(Taurus), Locust and other tools by either uploading JTL(csv) file or streaming data from the test run continuously. JtlReporter's main objective is to help you to understand your performance reports better and to spot performance regression.

## Features
* Detailed performance report
* Test run comparison
* Performance regression alerts
* Performance insights
* [and more](https://jtlreporter.site/docs/introduction/features).

## Used By
<img src="/assets/Logo-RedHat-A-Color-RGB.svg"  width="200" height="150">
<img src="https://github.com/ludeknovy/jtl-reporter/assets/13610612/189af2f0-fac1-47bf-b21d-ff424602a8a3", width="200", height ="150">



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

## Migration from v3 to v4
* Shut down the app but leave DB (postgres) running
* Backup you v3 DB!
* Run following query to modify the DB schema:
```
ALTER TABLE jtl.items 
DROP COLUMN data_id;
```
* Dump all of your data by running:
```
docker exec -t <container_name> pg_dumpall -a -U postgres > backup_v3.sql
```

* Import the data to v4 DB (make sure the DB is up):
```
docker exec -i <container_name>  psql -U postgres -d jtl_report < backup_v3.sql
```

If you use **Taurus**, see the needed changes in [upload script](https://github.com/ludeknovy/jtl-reporter/commit/ed477855c06cd790538c48d87b4fd6887729be33#diff-3b9f9f6188c06faceab5ea1d052c0a767a1e1925dce66fdc68e2ffcbe5c2aa3dL43
).
  
## Documentation 📖
For additional information please refer to the [documentation](https://jtlreporter.site/docs/).

## Analytics 
Currently, the following metrics are collected:
 * every 6 hours the backend application sends an event that the instance is alive
 * report processing is finished
 * the number of labels and duration of the test run
 
 If you don't want the analytics to be used, you can set `OPT_OUT_ANALYTICS` to `true` for backend service.
Mixpanel service is used for storing the data.


## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)
  * [listener](https://github.com/ludeknovy/jtl-reporter-listener-service)
  * [scheduler](https://github.com/ludeknovy/jtl-reporter-scheduler)
  * [docs](https://github.com/ludeknovy/jtl-reporter-docs)


## Screenshot
![Item detail](/assets/item_detail.png)

## License
Jtl Reporter is GNU Affero General Public License v3.0 licensed ([frontend](https://github.com/ludeknovy/jtl-reporter-fe/blob/master/LICENSE), [backend](https://github.com/ludeknovy/jtl-reporter-be/blob/master/LICENSE) and [listener](https://github.com/ludeknovy/jtl-reporter-listener-service/blob/main/LICENSE)). 

This repository is [MIT licensed.](LICENSE)
