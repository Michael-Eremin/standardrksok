# standardrksok
## standardrksok server

Standard for receiving and sending data.
Server according to this standard implemented on the example of a phone book.

РКСОК version 1.0 consists of four commands.

### Commands

ОТДОВАЙ — to get data.
УДОЛИ — to delete data.
ЗОПИШИ — for creating and updating data.
АМОЖНА? — to get command processing permission from the check base.
The first three commands are for working with client (and *"name_phone.json"*).
The fourth command is intended for communication between the server and the server (*"vragi-vezde"*) of special checking all requests.


### Process

The server receives the request.
The correctness of the request is checked. If the request is not correct, then return to the client that the request is not understood.
Permission is requested to process the request on the validation server. If refusal, then returns to the client the text of the refusal to process the request.
Request decryption.
Recording, deleting or obtaining information from the database (phone book file).
A response is being prepared to be sent to the client.
The server sends a response to the request to the client.


### Requirements to request/response.

An empty string (symbols \r\n\r\n) is the end of the client request. The request can consist of several lines.
The maximum name length in all scenarios is limited to 30 characters.
All responses from the server must also end with two line breaks \r\n\r\n, by these characters the client will understand that the request is finished and it can be processed.


### Code features

The code is implemented according to the principles of asynchrony.


### Composition

* server_rksok.py
* config.ini
* debug.log
* name_phone.json


### DevelopmentrRequirements

#### Python 3.10.2
* asyncio
* re
* json
* aiofiles
* loguru

#### Packages(pip_requirements.txt):
* aiofiles==0.8.0
* astroid==2.9.3
* isort==5.10.1
* lazy-object-proxy==1.7.1
* loguru==0.6.0
* mccabe==0.6.1
* platformdirs==2.5.0
* pylint==2.12.2
* toml==0.10.2
* wrapt==1.13.3


### Run server
#### On localhost:
* run the test server simulator *vragi-vezde.py* (generates responses to processing permission requests): **python vragi-vezde.py**
    specify in the code: *server = await asyncio.start_server(handle_echo, **'vragi-vezde', 5000**)*
    <br>
* start the command processing server: **python server_rksok.py**
    specify in config: [PROXY] IP = **127.0.0.1**, PORT = **8000**; [INSPECTOR] DOMAIN = **vragi-vezde**, PORT = **5000**
    <br>
* run the client application *rksok_client.py* for queries: **python rksok_client.py 127.0.0.1 8000**

#### Web request:
* run the client application for web-queries: **python rksok_client.py standardrksok.ru 8000**
