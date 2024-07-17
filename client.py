import sys
import csv
import socket
import json

def send_get_request(host, port, path):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    body = ''
    try:
        sock.connect((host, port))

        request_line = f'GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n'
        sock.send(request_line.encode())

        data = sock.recv(4096)
        response, _, body = data.partition(b'\r\n\r\n')

        status_line, _, header_data = response.partition(b'\r\n')
        protocol, status_code, message = status_line.split(b' ', 2)

        if status_code != b'200':
            print(f"Request failed with status {status_code.decode()} {message.decode()}")
            return None

        headers = {k.lower(): v.strip() for k, v in [line.split(': ', 1) for line in header_data.decode().split('\r\n') if ': ' in line]}
        content_length = int(headers.get('content-length', 0) if 'content-length' in headers else 0)

        while len(body) < content_length:
            body += sock.recv(4096)

        return json.loads(body)

    except Exception as ex:
        print(ex)
        if sock:
            sock.close()


def main(ip, port, analysis, output):
    if analysis == '1':
        data = send_get_request(ip, port, '/api/rank/sunk?limit=50&start=1')
        with open(output, 'w', newline='') as f:
            writer = csv.writer(f)
            for game in data['games']:
                writer.writerow([game['game_stats']['sunk'], game['game_stats']['average_sunk']])
    elif analysis == '2':
        data = send_get_request(ip, port, '/api/rank/escaped?limit=50&start=1')
        with open(output, 'w', newline='') as f:
            writer = csv.writer(f)
            for game in data['games']:
                writer.writerow([game['game_stats']['normalized_cannon_placement'], game['game_stats']['average_escaped']])
    else:
        print("Invalid analysis type. Please select 1 or 2.")

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: ./client <IP> <port> <analysis> <output>")
    else:
        main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])