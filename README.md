# SimpleHttpServer

### Simple http-server

Implements a part of http-server functionality. Handle GET, HEAD requests.

### Server architecture

Implements thread pool architecture

### Requirements

You need Python 3.0 or later

### Using

To start server execute:

```
python3  -m httpd
```  

Server starts at 8080 port. 


## Running the tests

To run tests execute in the project directoryl:

```
python3  -m unittest 
```  

## Loading tests results

Loading tests were done with apache ab in CentOS

```
ab -n 50000 -c 100 -r http://localhost:8080/
```

The following results were received:

```
Server Software:        SimpleHttpServer/1.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   129.470 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      5650000 bytes
HTML transferred:       0 bytes
Requests per second:    386.19 [#/sec] (mean)
Time per request:       258.940 [ms] (mean)
Time per request:       2.589 [ms] (mean, across all concurrent requests)
Transfer rate:          42.62 [Kbytes/sec] received

Connection Times (ms)
min  mean[+/-sd] median   max
Connect:        0    2  46.2      0    1066
Processing:     4  256 167.1    256   14040
Waiting:        3  252 167.1    252   14034
Total:          4  259 190.5    256   15102

Percentage of the requests served within a certain time (ms)
50%    256
66%    262
75%    266
80%    268
90%    275
95%    281
98%    297
99%    321
100%  15102 (longest request)
```

