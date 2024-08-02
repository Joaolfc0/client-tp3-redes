import sys
import csv
import socket
import json
from collections import defaultdict


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
            print(f"Request failed with status {
                  status_code.decode()} {message.decode()}")
            return None

        headers = {k.lower(): v.strip() for k, v in [line.split(
            ': ', 1) for line in header_data.decode().split('\r\n') if ': ' in line]}
        content_length = int(headers.get('content-length', 0)
                             if 'content-length' in headers else 0)

        while len(body) < content_length:
            body += sock.recv(4096)

        return json.loads(body)

    except Exception as ex:
        print(ex)
        if sock:
            sock.close()


def get_data(host, port, path):
    start = 1
    limit = 50
    final_data = []

    while start < 101:
        data = send_get_request(host, port, f'{path}&start={
                                start}&limit={limit}')
        if data is not None and 'games' in data:
            final_data.extend(data['games'])
            start += limit
        else:
            break

    return final_data


def get_gas_data(data):
    gas_data = {}

    for game in data:
        if game['auth'] not in gas_data:
            gas_data[game['auth']] = {'game_count': 1,
                                      'total_sunk_ships': game['sunk_ships']}
        else:
            gas_data[game['auth']]['game_count'] += 1
            gas_data[game['auth']]['total_sunk_ships'] += game['sunk_ships']

    for value in gas_data.values():
        value['average_sunk_ships'] = value['total_sunk_ships'] / \
            value['game_count']

    return gas_data


def normalize_cannon_placements(cannon_data):
    cannon_counts = [0] * 8
    for row in cannon_data:
        cannon_counts[len(row) - 1] += 1
    return ''.join(map(str, cannon_counts))


def generate_csv(gas_data, output_file):
    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        for gas, game_data in gas_data.items():
            writer.writerow([gas, game_data['game_count'],
                            game_data['average_sunk_ships']])


def main(ip, port, analysis, output):
    data = None

    if analysis == '1':
        path = '/api/rank/sunk?'
        data = get_data(ip, port, path)
        gas_data = get_gas_data(data)
        generate_csv(gas_data, output)

    elif analysis == '2':
        path = '/api/rank/escaped?limit=50'
        data = get_data(ip, port, path)
        cannon_stats = defaultdict(lambda: [0, 0])

        for game in data:
            normalized_placement = normalize_cannon_placements(game['cannons'])
            cannon_stats[normalized_placement][0] += game['escaped_ships']
            cannon_stats[normalized_placement][1] += 1

        averages = []
        for placement, (total_escaped, count) in cannon_stats.items():
            averages.append((placement, total_escaped / count))

        averages.sort(key=lambda x: x[1])

        with open(output, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            for placement, avg_escaped in averages:
                csvwriter.writerow([placement, avg_escaped])

    else:
        print("Invalid analysis type. Please select 1 or 2.")
        return


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: <IP> <port> <analysis> <output>")
    else:
        main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])
