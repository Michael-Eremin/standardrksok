'''Response generation server'''
import asyncio
import random


async def handle_echo(reader, writer):
    '''Read request, write and send response, close socket connection'''

    data = await reader.read(1024)
    message = data.decode('utf-8')
    addr = writer.get_extra_info('peername')
    print(f"Received {message!r} from {addr!r}")
    random_response = random.randint(0, 1)
    if random_response == 0:
        msg_response = 'МОЖНА РКСОК/1.0\r\n\r\n'
    else:
        msg_response = "НИЛЬЗЯ РКСОК/1.0\r\nКто ещё такой? Он тебе зачем?\r\n\r\n"
    print(f"Send: {msg_response!r}")
    writer.write(msg_response.encode("utf-8"))
    await writer.drain()
    print("Close the connection")
    writer.close()


async def main():
    '''Start socket'''
    server = await asyncio.start_server(
        handle_echo, 'vragi-vezde', 5000)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()


# Start server
asyncio.run(main())
