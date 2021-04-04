<h1 align="center">JtlReporter</h1>

![jtl gif](/assets/jtl.gif)

## Description
Online reporting application to generate reports from JMeter(Taurus), Locust, and other tools by either uploading JTL(csv) file or streaming data from the test run continuously. Jtl Reporter's main objective is to help you to understand your performance reports better and help you to spot performance regression.

## Features
#### Detailed performance report
JtlReport will provide you with metrics for each label (endpoint call) such as requests per seconds, various percentiles, error rate and more. It will provide you the overall stats as well, eg: the total throughput (RPS), 90% percentile, network data transferred (mbps). Besides the prepared charts (throughput, response times, network, and so on), you can create your custom chart from the available metrics to further explore the performance report.

#### Test run comparison
If you want to compare HTML reports, you need to open them side by side and look for the differences and correlations on your own. With JtlReporter that comparison is only four clicks away. And it does not stop there. You can even drill down in response time and throughput trends for each label (endpoint call).

#### Performance regression alerts
If you run your performance tests regularly as a part of your delivery pipeline, you might set up performance thresholds for response time, error rate, and throughput. With each new report processing, it checks the long-term averages for the same environment. In case the performance did degrade above set up thresholds, you will get an alert in the report detail.

#### Performance insights
JtlReport will perform some performance analysis automatically for you. It aims to help you to interpret the outcome of the measurements and warn you if there might be an issue related to an overloaded system under tests. Currently, the application checks three metrics, and if any of them evinces poor performance it will mark it and provide you with the details.

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
## Integration. How to get log data in

### Manually via UI
This is the easiest and fastest way if you want to try out this application. 

You have to create a new project and scenario before you can upload any performance test data. To a create new project click on the user icon at the top menu, then **administrate** —> **add project**. Enter the project name and confirm. Now head to project detail by selecting it from the projects dropdown at the top menu and click **add new scenario**. Enter the scenario name and confirm. Open its detail by clicking on its name. 

Once you are in the scenario detail you click the **Add test run** button, where you can upload a `.jtl` file and fill in other related information. Once you hit **Submit** button you should get confirmation. Once the `.jtl` file is processed you will see the new item in the listing.

### Taurus integration
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

Launch your test and after it finishes it will upload .jtl file(s) into Jtl Reporter automatically.

Please note that "demoProject" and "demoScenario" have to exist in Jtl Reporter beforehand otherwise it will return an error.

### Locust.io integration

You have two options here - generate JTL file and upload it to the application, or use JTL listener service and upload the results continuous while running your test.

**Please note that the below-mentioned listeners currenty support only distributed mode.**

#### Generating and uploading JTL file
Download [jtl_listener.py](/scripts/jtl_listener.py) into your locust project folder.

Register the listener in your locust test by placing event listener at the very end of the file:
```
from jtl_listener import JtlListener

...

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    JtlListener(env=environment,  project_name="project name",
                scenario_name="scenario name",
                environment="tested envitonment",
                backend_url="http://IP_ADDRESS")
```

Generate api token in the application and set it as `JTL_API_TOKEN` env variable.

After the test finishes you will find a jtl file in `logs` folder. 

~~Because of this [issue](https://github.com/locustio/locust/issues/1638) it's not possible to upload the file automatically.~~

#### Continuous results uploading
Download [jtl_listener_service.py](/scripts/jtl_listener_service.py) into your locust project folder.

Register the listener in your locust test by placing event listener at the very end of the file:
```
from jtl_listener_service import JtlListener

...

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    JtlListener(env=environment,  project_name="project name",
                scenario_name="scenario name",
                hostname="hostname",
                backend_url="http://IP_ADDRESS")
```

Generate api token in the application and set it as `JTL_API_TOKEN` env variable.

Once you run your test, the plugin will start uploading results to [jtl listener service](https://github.com/ludeknovy/jtl-reporter-listener-service).

## JMeter Distributed Mode
* If you run your tests in distributed mode you need to provide `Hostname` in csv output.
You can do it by setting `jmeter.save.saveservice.hostname=true` in `jmeter.properties`

## Uploading large JTL file
If you plan to upload large JTL file, you need to change mongo settings like this:
```
let newLimit = 1000 * 1024 * 1024;
db.adminCommand({setParameter: 1, internalQueryMaxPushBytes: newLimit});
```

Otherwise mongo will throw error like this:
```
MongoError: $push used too much memory and cannot spill to disk. Memory limit: 104857600 bytes",
```

## Repositories structure
 JtlReporter consists of the following parts:
  * [backend](https://github.com/ludeknovy/jtl-reporter-be)
  * [frontend](https://github.com/ludeknovy/jtl-reporter-fe)
  * [listener](https://github.com/ludeknovy/jtl-reporter-listener-service)


## Screenshot
![Item detail](/assets/item_detail.png)

## License
Jtl Reporter is [GPL-3.0 licensed.](LICENSE)  
