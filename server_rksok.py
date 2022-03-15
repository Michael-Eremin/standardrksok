"""Server for receiving requests and sending responses to the client according to the RKSOK standard 'РКСОК/1.0'."""
import asyncio
import re
import json
import aiofiles
from loguru import logger

logger.add("debug.log", format="{time} {level} {message}", level="DEBUG", rotation="50 KB")


#Basic constants
PROTOCOL = "РКСОК/1.0"
ENCODING = "UTF-8"
REQUEST_METHODS = {
    "ОТДОВАЙ": "GET",
    "УДОЛИ": "DELETE",
    "ЗОПИШИ": "WRITE",
}

async def write_to_file (phone_book: str, data : str) -> str:
    """Writes the new name and phone number (or just the phone number if the name exists) to the phonebook file."""
    name_phone = json.dumps(data, ensure_ascii=False)
    logger.info(f'name_phone:{name_phone!r}')
    async with aiofiles.open(phone_book, mode='w') as f:
        await f.write(name_phone)


async def read_from_file(name_file: str) -> str or None:
    """"Reads the phone by name from the phonebook file."""
    async with aiofiles.open(name_file, mode='r') as f:
        data_from_phone_book = await f.read()
        if data_from_phone_book:
            string_from_file = str(data_from_phone_book)
        else:
            string_from_file = None
    logger.info(f'string_from_file:{string_from_file!r}')
    return string_from_file


async def get_phone_by_name(name: str, data: str) -> str:
    """Gets a phone from the phonebook."""
    if data:
        if name in data:
            phone = list(data[name])
            phone_to_msg = ''
            for data_phone in phone:
                phone_to_msg += data_phone + '\r\n'
            message_for_get_phone = f'НОРМАЛДЫКС РКСОК/1.0\r\n{phone_to_msg}\r\n'
        else:
            message_for_get_phone = 'НИНАШОЛ РКСОК/1.0\r\n\r\n'
    else:
        message_for_get_phone = 'НИНАШОЛ РКСОК/1.0\r\n\r\n'
    logger.info(f'message_for_get_phone:{message_for_get_phone!r}')
    return message_for_get_phone


async def delete_name(name: str, data: str) -> str:
    """Removes the name with phone from the phonebook."""
    if data:
        if name in data:
            data_to_file = dict(data)
            del data_to_file[name]
            await write_to_file('name_phone.json', data_to_file)
            message_for_delete_name = 'НОРМАЛДЫКС РКСОК/1.0\r\n\r\n'
        else:
            message_for_delete_name = 'НИНАШОЛ РКСОК/1.0\r\n\r\n'
    else:
        message_for_delete_name = 'НИНАШОЛ РКСОК/1.0\r\n\r\n'
    logger.info(f'message_for_delete_name:{message_for_delete_name!r}')
    return message_for_delete_name


async def write_name_phone(name: str, data_from_file: str, data_phone: str, \
    length_data: int) -> str:
    """Writes a new name with a phone number or a new phone number with an existing name in the phone book"""
    #Gathering all request phones into a tuple.
    phone = ()
    for data in data_phone[1:(length_data-2)]:
        if data:
            phone += (data,)
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


async def make_msg_to_client(message_received: str) -> str:
    "Reads the request, creats a response to the client."
    name_for_phone = re.split(r' ', message_received.split(PROTOCOL)[0], \
        maxsplit = 1)[-1].strip().upper()
    data_from_name_phone = await read_from_file('name_phone.json')
    data_from_file = json.loads(data_from_name_phone)
    if message_received.split()[0] == "ОТДОВАЙ":
        message_to_client = await get_phone_by_name(name_for_phone, data_from_file)
    elif message_received.split()[0] == "УДОЛИ":
        message_to_client = await delete_name(name_for_phone, data_from_file)
    elif message_received.split()[0] == "ЗОПИШИ":
        #List of request data that comes after the Protocol.
        data_phone = re.split(r'\r\n', message_received.split(PROTOCOL)[1])
        length_data = len(data_phone)
        await write_name_phone(name_for_phone, data_from_file, data_phone, \
            length_data)
        message_to_client = 'НОРМАЛДЫКС РКСОК/1.0\r\n\r\n'
    else:
        message_to_client = 'НИПОНЯЛ РКСОК/1.0\r\n\r\n'
    logger.info(f'message_to_client:{message_to_client!r}')
    return message_to_client


async def make_response_to_client(msg_from_vragi_vezde, msg_received):
    "If the 'vragi-vezde.to.digital' server allowed the response, then we produce a full response. If the server received a refusal, then instead of a response, we send only a refusal."
    if msg_from_vragi_vezde == 'МОЖНА РКСОК/1.0\r\n\r\n':
        response_to_client = await make_msg_to_client(msg_received) 
    else:
        response_to_client = f'{msg_from_vragi_vezde}'
    logger.info(f'response_to_client:{response_to_client!r}')
    return response_to_client


async def send_reciev_vragi_vezde(message: str) ->str:
    """Sends a request, receives a response from the server 'vragi-vezde'."""
    try:
        reader, writer = await asyncio.open_connection \
            ('vragi-vezde.to.digital', 51624)
        writer.write(message.encode(ENCODING))
        data = await reader.read(1024)
        msg_from_vragi_vezde = data.decode(ENCODING)
        writer.close()
        logger.info(f'From "vragi vezde:{msg_from_vragi_vezde!r}')
        return msg_from_vragi_vezde
    except ConnectionRefusedError:
        logger.debug('Unable to connect to server "vragi-vezde.to.digital".')
    


async def check_request_client(row_request: str) -> bool:
    """Checks the correctness of the received request. Checks for the presence in the query string: Protocol Name, Protocol Method, the number of Name characters is not more than 30."""
    if PROTOCOL in row_request and row_request.split()[0] in REQUEST_METHODS:
        len_of_name = len(re.split(r' ', row_request.split(PROTOCOL)[0], maxsplit = 1)[-1].strip())
        if 0 < len_of_name <= 30:
            correctness_request = True
        else:
            correctness_request = False
    else:
        correctness_request = False
    logger.info(f"correctness_request: {correctness_request!r}")
    return correctness_request
    


async def reciev_send_client(reader: str, writer: str) ->str:
    """Receives a request, if the request is correct, then sends it for verification to server 'vragi-vezde', after preparing a response to a request, send a response to the client."""
    data = await reader.read(1024)
    #We get the first part of the request.                             
    msg_received = data.decode(ENCODING)                                       
    addr = writer.get_extra_info('peername')
    logger.info(f"Start received from {addr!r}: {msg_received!r}")
    #If there is no end value '\r\n\r\n' in the first part of the received request, continue reading the request.
    if msg_received[-4:]!= '\r\n\r\n':
        while True:
            data = await reader.read(1024)
            msg_received += data.decode(ENCODING)
            #We continue to read the request, wait for the value of the end '\r\n\r\n' and insure against a broken connection.
            if not msg_received or msg_received[-4:] == '\r\n\r\n':
                break
    logger.info(f"Final received from {addr!r}: {msg_received!r}")
    #If the request is correct, we produce a response 'msg_response'.
    if await check_request_client(msg_received):
        msg_to_vragi_vezde = f'АМОЖНА? РКСОК/1.0\r\n{msg_received}'
        msg_from_vragi_vezde =  await send_reciev_vragi_vezde(msg_to_vragi_vezde)
        msg_response = await make_response_to_client(msg_from_vragi_vezde, msg_received)
    else:
        msg_response = 'НИПОНЯЛ РКСОК/1.0\r\n\r\n'
    #Submitting a response 'msg_response'.
    writer.write(msg_response.encode(ENCODING))
    await writer.drain()
    logger.info(f"Send to client: {msg_response!r}")
    logger.info("Close the connection")
    writer.close()


async def main():
    "Server start."
    server = await asyncio.start_server(reciev_send_client, \
        '0.0.0.0', 8000)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('The server has been stopped by someone.')
