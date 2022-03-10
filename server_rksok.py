"""Server for receiving requests and sending responses to the client according to the RKSOK standard."""
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
    async with aiofiles.open(phone_book, mode='w') as f:
        await f.write(name_phone)


async def read_from_file(name_file: str) -> str or None:
    """"Reads the phone by name from the phonebook file."""
    async with aiofiles.open(name_file, mode='r') as f:
        data_from_phone_book = await f.read()
        if data_from_phone_book:
            string_from_file = json.loads(data_from_phone_book)
        else:
            string_from_file = None
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
    return message_for_delete_name


async def write_name_phone(name: str, data_from_file: str, data_phone: str, \
    length_data: int) -> str:
    """Writes a new name with a phone number or a new phone number with an existing name in the phone book"""
    phone = ()
    for data in data_phone[1:(length_data-2)]:
        if data:
            phone += (data,)
    if data_from_file:
        if name in data_from_file:
            existing_phone = tuple(data_from_file[name])
            updated_phone = existing_phone + phone
            data_from_file[name] = updated_phone
            data_to_file = data_from_file
            await write_to_file('name_phone.json', data_to_file)
        else:
            data_from_file[name] = phone
            data_to_file = data_from_file
            await write_to_file('name_phone.json', data_to_file)
    else:
        new_dict = {}
        new_dict[name] = phone
        data_to_file = new_dict
        await write_to_file('name_phone.json', data_to_file)


async def make_msg_to_client(message_received: str) -> str:
    "Reads the request, prepares a response to the client."
    name_for_phone = re.split(r' ', message_received.split(PROTOCOL)[0], \
        maxsplit = 1)[-1].strip().upper()
    data_from_file = await read_from_file('name_phone.json')
    if message_received.split()[0] == "ОТДОВАЙ":
        message_to_client = await get_phone_by_name(name_for_phone, data_from_file)
    elif message_received.split()[0] == "УДОЛИ":
        message_to_client = await delete_name(name_for_phone, data_from_file)
    elif message_received.split()[0] == "ЗОПИШИ":
        data_phone = re.split(r'\r\n', message_received.split(PROTOCOL)[1])
        length_data = len(data_phone)
        await write_name_phone(name_for_phone, data_from_file, data_phone, \
            length_data)
        message_to_client = 'НОРМАЛДЫКС РКСОК/1.0\r\n\r\n'
    else:
        message_to_client = 'НИПОНЯЛ РКСОК/1.0\r\n\r\n'
    return message_to_client


async def make_response_to_client(msg_from_vragi_vezde, msg_received):
    "Rtf"
    if msg_from_vragi_vezde == 'МОЖНА РКСОК/1.0':
        response_to_client = await make_msg_to_client(msg_received) 
    else:
        response_to_client = f'{msg_from_vragi_vezde}'
    
    return response_to_client


async def send_reciev_vragi_vezde(message: str) ->str:
    """Sends a request, receives a response from the server 'vragi-vezde'."""
    reader, writer = await asyncio.open_connection \
        ('vragi-vezde.to.digital', 5000)
    writer.write(message.encode(ENCODING))
    data = await reader.read(1024)
    msg_from_vragi_vezde = data.decode(ENCODING)
    writer.close()
    logger.info(f'From "vragi vezde":{msg_from_vragi_vezde}')
    return msg_from_vragi_vezde


async def check_request_client(row_request: str) -> bool:
    """Checks the correctness of the received request."""
    if PROTOCOL in row_request and row_request.split()[0] in REQUEST_METHODS:
        len_of_name = len(re.split(r' ', row_request.split(PROTOCOL)[0], maxsplit = 1)[-1].strip())
        if 0 < len_of_name <= 30:
            correctness_request = True
        else:
            correctness_request = False
    else:
        correctness_request = False
    return correctness_request


async def reciev_send_client(reader: str, writer: str) ->str:
    """Receives a request, if the request is correct, then sends it for verification to server 'vragi-vezde', after preparing a response to a request, send a response to the client."""
    data = await reader.read(1024)
    msg_received = data.decode(ENCODING)
    if msg_received[-4:]!= '\r\n\r\n':
        while True:
            data = await reader.read(1024)
            msg_received += data.decode(ENCODING)
            if msg_received[-4:] == '\r\n\r\n':
                break
    else:
        addr = writer.get_extra_info('peername')
        logger.info(f"Received from {addr!r}: {msg_received!r}")
    if await check_request_client(msg_received):
        msg_to_vragi_vezde = f'АМОЖНА? РКСОК/1.0\r\n{msg_received}'
        msg_from_vragi_vezde =  await send_reciev_vragi_vezde(msg_to_vragi_vezde)
        msg_response = await make_response_to_client(msg_from_vragi_vezde, msg_received)
    else:
        msg_response = 'НИПОНЯЛ РКСОК/1.0\r\n\r\n'
    writer.write(msg_response.encode(ENCODING))
    await writer.drain()
    logger.info(f"Send: {msg_response!r}")
    logger.info("Close the connection")
    writer.close()


async def main():
    "Rtf."
    server = await asyncio.start_server(reciev_send_client, \
        '127.0.0.1', 8000)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()

asyncio.run(main())