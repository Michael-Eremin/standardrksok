"""Server for receiving requests and sending responses to the client according to the RKSOK standard 'РКСОК/1.0'."""
import asyncio
import re
import json
from configparser import ConfigParser
from loguru import logger
import aiofiles


# Read from "config.ini"
config = ConfigParser()
config.read("config.ini")

# Logging
logger.add("debug.log", format="{time} {level} {message}", level="DEBUG", rotation="12:00")

# Line endings
END_S = '\r\n'
EMPTY_S = '\r\n\r\n'
# Conversion to bytes
EMPTY_S_B = EMPTY_S.encode(config['SETTINGS']['ENCODING'])
GET_B = config['REQUEST_METHODS']['GET'].encode(config['SETTINGS']['ENCODING'])
DELETE_B = config['REQUEST_METHODS']['DELETE'].encode(config['SETTINGS']['ENCODING'])
WRITE_B = config['REQUEST_METHODS']['WRITE'].encode(config['SETTINGS']['ENCODING'])


async def write_to_file (phone_book: str, data : dict) -> json:
    """Writes the new name and phone number (or just the phone number if the name exists) to the phonebook file."""
    name_phone = json.dumps(data, ensure_ascii=False)
    logger.info(f'name_phone:{name_phone!r}')
    async with aiofiles.open(phone_book, mode='w') as f:
        await f.write(name_phone)


async def read_from_file(name_file: str) -> json or None:
    """"Reads the phone by name from the phonebook file."""
    async with aiofiles.open(name_file, mode='r') as f:
        data_from_phone_book = await f.read()
        if data_from_phone_book:
            string_from_file = str(data_from_phone_book)
        else:
            string_from_file = None
    logger.info(f'string_from_file:{string_from_file!r}')
    return string_from_file


async def get_phone_by_name(name: str) -> str:
    """Gets a phone from the phonebook."""
    data_conf = config['RESPONSE']
    data_from_name_phone = await read_from_file('name_phone.json')
    data = json.loads(data_from_name_phone)
    if data:
        if name in data:    
            phone = list(data[name])
            phone_to_msg = ''
            for data_phone in phone:
                phone_to_msg += data_phone + END_S
            message_for_get_phone = f"{data_conf['normally']}{END_S}{phone_to_msg}{END_S}"
        else:
            message_for_get_phone = f"{data_conf['not_found']}{EMPTY_S}"
    else:
        message_for_get_phone = f"{data_conf['not_found']}{EMPTY_S}"
    logger.info(f'message_for_get_phone:{message_for_get_phone!r}')
    return message_for_get_phone


async def delete_name(name: str) -> str:
    """Removes the name with phone from the phonebook."""
    data_conf = config['RESPONSE']
    data_from_name_phone = await read_from_file('name_phone.json')
    data = json.loads(data_from_name_phone)
    if data:
        if name in data:
            data_to_file = dict(data)
            del data_to_file[name]
            await write_to_file('name_phone.json', data_to_file)
            message_for_delete_name = f"{data_conf['normally']}{EMPTY_S}"
        else:
            message_for_delete_name = f"{data_conf['not_found']}{EMPTY_S}"
    else:
        message_for_delete_name = f"{data_conf['not_found']}{EMPTY_S}"
    logger.info(f'message_for_delete_name:{message_for_delete_name!r}')
    return message_for_delete_name


async def write_name_phone(name: str, data_phone: str):
    """Writes a new name with a phone number or a new phone number with an existing name in the phone book"""
    #Gathering all request phones into a tuple.
    data_from_name_phone = await read_from_file('name_phone.json')
    data_from_file = json.loads(data_from_name_phone)
    length_data_phone = len(data_phone)
    phone = ()
    for number in data_phone[1:(length_data_phone-2)]:
        if number:
            phone += (number,)
    if data_from_file:
        #If the name is in the phone book, then we change the existing phone to a new phone.
        if name in data_from_file:
            data_from_file[name] = phone
            data_to_file = data_from_file
            logger.info(f'data_to_file:{data_to_file!r}')
            await write_to_file('name_phone.json', data_to_file)
        else:
            data_from_file[name] = phone
            data_to_file = data_from_file
            logger.info(f'data_to_file:{data_to_file!r}')
            await write_to_file('name_phone.json', data_to_file)
    else:
        #For the first request 'write_name_phone'.
        new_dict = {}
        new_dict[name] = phone
        data_to_file = new_dict
        logger.info(f'data_to_file:{data_to_file!r}')
        await write_to_file('name_phone.json', data_to_file)


async def parse_message_received(message_received: str) -> tuple[str, str]:
    """Get from the query string: method, name, phone."""
    name_for_phone = re.split(r' ', message_received.split(config['REQUEST_METHODS']['PROTOCOL'])[0], \
         maxsplit = 1)[-1].strip().upper()
    method = message_received.split()[0]
    if method == config['REQUEST_METHODS']['WRITE']:
        data_phone = re.split(rf'{END_S}', message_received.split(config['REQUEST_METHODS']['PROTOCOL'])[1])
        parse_tuple = (method, name_for_phone, data_phone)
    else:
        parse_tuple = (method, name_for_phone)
    return parse_tuple
    

async def make_msg_to_client_if_get(name: str) -> str:
    """Make message if method in the request is 'ОТДОВАЙ'."""
    message = await get_phone_by_name(name)
    logger.info(f'message_to_client:{message!r}')
    return message


async def make_msg_to_client_if_delete(name: str) -> str:
    """Make message to the client if method in the request is 'УДОЛИ'."""
    message = await delete_name(name)
    logger.info(f'message_to_client:{message!r}')
    return message


async def make_msg_to_client_if_write(name: str, data_phone: str) -> str:
    """Make message to the client if method in the request is 'ЗОПИШИ'."""
    await write_name_phone(name, data_phone)
    message = f"{config['RESPONSE']['normally']}{EMPTY_S}"
    logger.info(f'message_to_client:{message!r}')
    return message


async def make_msg_to_client(parse_tuple: tuple[str, str]) -> str:
    """Prepares message to the client."""
    data_conf = config['REQUEST_METHODS']
    method = parse_tuple[0]
    if method == data_conf['GET']:
        message_to_client = await make_msg_to_client_if_get(parse_tuple[1])
    elif method == data_conf['DELETE']:
        message_to_client = await make_msg_to_client_if_delete(parse_tuple[1])
    elif method == data_conf['WRITE']:
        message_to_client = await make_msg_to_client_if_write(parse_tuple[1], parse_tuple[2])
    return message_to_client


async def make_response_to_client(msg_from_vragi_vezde: str, msg_received: str) -> str:
    "If the 'vragi-vezde.to.digital' server allowed the response, then we produce a full response. If the server received a refusal, then instead of a response, we send only a refusal."
    if msg_from_vragi_vezde == f"{config['INSPECTOR']['response_yes']}{EMPTY_S}":
        parse_tuple = await parse_message_received(msg_received)
        response_to_client = await make_msg_to_client(parse_tuple)
    else:
        response_to_client = f'{msg_from_vragi_vezde}'
    logger.info(f'response_to_client:{response_to_client!r}')
    return response_to_client


async def send_reciev_vragi_vezde(message: str) ->str:
    """Sends a request, receives a response from the server 'vragi-vezde'."""
    try:
        reader, writer = await asyncio.open_connection \
            (config['INSPECTOR']['DOMAIN'], config['INSPECTOR']['PORT'])
        writer.write(message.encode(config['SETTINGS']['ENCODING']))
        data = await reader.read(1024)
        msg_from_vragi_vezde = data.decode(config['SETTINGS']['ENCODING'])
        writer.close()
        logger.info(f'From "vragi vezde:{msg_from_vragi_vezde!r}')
        return msg_from_vragi_vezde
    except ConnectionRefusedError:
        logger.debug('Unable to connect to server "vragi-vezde.to.digital".')


async def check_request_client(raw_request: str) -> bool:
    """Checks the correctness of the received request. Checks for the presence in the query string: Protocol Name, Protocol Method, the number of Name characters is not more than 30."""
    data_conf = config['REQUEST_METHODS']
    methods = {data_conf['GET'], data_conf['DELETE'], data_conf['WRITE']}
    if data_conf['PROTOCOL'] in raw_request and raw_request.split()[0] in methods:
        len_of_name = len(re.split(r' ', raw_request.split(data_conf['PROTOCOL'])[0], maxsplit = 1)[-1].strip())
        if 0 < len_of_name <= int(data_conf['len_name']):
            correctness_request = True
        else:
            correctness_request = False
    else:
        correctness_request = False
    logger.info(f"correctness_request: {correctness_request!r}")
    return correctness_request


async def response_preparation(msg_received: str) ->str:
    """Preparing a response to a request."""
    # If the request is correct, we produce a response 'msg_response'.
    if await check_request_client(msg_received):
        msg_to_vragi_vezde = f"{config['INSPECTOR'] ['request']}{END_S}{msg_received}"
        msg_from_vragi_vezde =  await send_reciev_vragi_vezde(msg_to_vragi_vezde)
        msg_response = await make_response_to_client(msg_from_vragi_vezde, msg_received)
    else:
        msg_response = f"{config['RESPONSE']['unclear']}{EMPTY_S}"
    return msg_response


async def check_first_100_bytes(data: bytes) -> bool:
    "Checks for protocol methods."
    if data.startswith(GET_B) or data.startswith(DELETE_B) or data.startswith(WRITE_B):
        return True


async def reciev_send_client(reader: asyncio.streams.StreamReader, writer: asyncio.streams.StreamWriter):
    """Receives a request, if the request is correct, then sends it for preparing a response to a request."""
    data = await reader.read(100)
    # Get the first part of the request.                             
    addr = writer.get_extra_info('peername')
    logger.info(f"First 100 bytes received from {addr!r}{data}")    
    # Spam Protection
    if not await check_first_100_bytes(data):
        logger.info(f"Received unknown protocol from {addr!r}: {data}")
        # msg_response = str (config['RESPONSE']['unclear'] + EMPTY_S)
        msg_response = f"{config['RESPONSE']['unclear']}{EMPTY_S}"
    else:    
        # If there is no end value '\r\n\r\n' in the first part of the received request, continue reading the request.
        if not data.endswith(EMPTY_S_B):
            while True:
                data += await reader.read(1024)
                # We continue to read the request, wait for the value of the end '\r\n\r\n' and insure against a broken connection.
                if not data or data.endswith(EMPTY_S_B):
                    break
            msg_received = data.decode(config['SETTINGS']['ENCODING'])
            logger.info(f"Received more than 100 bytes from {addr!r}: {msg_received!r}")
            msg_response = await response_preparation(msg_received)
        else:
            msg_received = data.decode(config['SETTINGS']['ENCODING'])
            logger.info(f"Received from {addr!r}: {msg_received!r}")
            msg_response = await response_preparation(msg_received)    
    # Submitting a response 'msg_response'.
    writer.write(msg_response.encode(config['SETTINGS']['ENCODING']))
    await writer.drain()
    logger.info(f"Send to client: {msg_response!r}")
    logger.info("Close the connection")
    writer.close()


async def main():
    "Server start."
    data_conf = config['PROXY']
    server = await asyncio.start_server(reciev_send_client, \
        data_conf['IP'], data_conf['PORT'])
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('The server has been stopped by someone.')
