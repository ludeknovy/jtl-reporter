<h1 align="center">JtlReporter</h1>

![jtl gif](/assets/jtl.gif)

## Description
 Reporting tool for [Taurus](https://gettaurus.org)(JMeter) load tests. Jtl Reporter is meant to be used as addition to Grafana perf stack. While Grafana provides great solution for live data preview it falls short of easy test run retrospective. Jtl Reporter's main objective is to give you the possibility compare test runs with ease.

More on [blog](https://www.ludeknovy.tech/blog/generate-intuitive-jmeter-reports-with-jtlreporter-and-taurus/)

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

Launch your test and after it finishes it will upload .jtl file(s) into Jtl Reporter automatically.

Please note that "demoProject" and "demoScenario" have to exist in Jtl Reporter beforehand otherwise it will return an error.

## Locust.io integration
Download [jtl_listener.py](/scripts/jtl_listener.py) into your locust project folder.

Register the listener in your locust test by placing event listener at the very end of the file:
```
from jtl_listener import JtlListener

...

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    JtlListener(env=environment)
```

After the test finishes you will find a jtl file in `logs` folder. 

~~Because of this [issue](https://github.com/locustio/locust/issues/1638) it's not possible to upload the file automatically.~~

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
