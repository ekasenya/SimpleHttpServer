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
Document Length:        167 bytes

Concurrency Level:      100
Time taken for tests:   266.717 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      15950000 bytes
HTML transferred:       8350000 bytes
Requests per second:    187.46 [#/sec] (mean)
Time per request:       533.434 [ms] (mean)
Time per request:       5.334 [ms] (mean, across all concurrent requests)
Transfer rate:          58.40 [Kbytes/sec] received

Connection Times (ms)
min  mean[+/-sd] median   max
Connect:        0    2  39.7      0    1045
Processing:    21  531 341.2    444   13738
Waiting:        7  517 335.9    433   13725
Total:         22  533 352.0    445   14781

Percentage of the requests served within a certain time (ms)
50%    445
66%    484
75%    526
80%    565
90%    762
95%    926
98%   1167
99%   1483
100%  14781 (longest request)
```

