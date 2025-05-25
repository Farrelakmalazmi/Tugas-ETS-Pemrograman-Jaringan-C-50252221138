import socket
import os
import base64
import concurrent.futures
import threading
import sys
import time
import uuid

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8995
BUFFER_SIZE = 1048576  # 1MB
FILES_DIR = 'server_files'
SOCKET_TIMEOUT = 60

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

success_count = 0
fail_count = 0
lock = threading.Lock()

def process_task(command, args):
    try:
        if command == 'LIST':
            files = os.listdir(FILES_DIR)
            response = '\n'.join(files) if files else 'No files found.'
            return response.encode()

        elif command == 'UPLOAD_FROM_FILE':
            filename, b64filepath = args
            try:
                if not os.path.exists(b64filepath):
                    return f'Error: Temp file not found {b64filepath}'.encode()

                with open(b64filepath, 'rb') as f:
                    encoded_data = f.read()
                decoded_data = base64.b64decode(encoded_data)

                final_path = os.path.join(FILES_DIR, filename)
                with open(final_path, 'wb') as f:
                    f.write(decoded_data)

                os.remove(b64filepath)
                return b'Upload successful'
            except Exception as e:
                return f'Error during upload from file: {str(e)}'.encode()

        elif command == 'DOWNLOAD':
            filename = args
            filepath = os.path.join(FILES_DIR, filename)
            if not os.path.exists(filepath):
                return b'File not found'
            with open(filepath, 'rb') as f:
                file_data = f.read()
            encoded_data = base64.b64encode(file_data)
            return encoded_data + b'__END__'

        else:
            return b'Unknown command'

    except Exception as e:
        return f'Error: {str(e)}'.encode()

def print_status_periodically():
    global success_count, fail_count
    while True:
        time.sleep(10)
        with lock:
            print(f"[Server Status] Success count: {success_count}, Fail count: {fail_count}")

def handle_client(conn, addr, pool):
    global success_count, fail_count
    print(f"[+] Menangani koneksi dari {addr}")

    try:
        conn.settimeout(SOCKET_TIMEOUT)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        data = conn.recv(BUFFER_SIZE).decode()
        if not data:
            with lock:
                fail_count += 1
            return

        parts = data.strip().split()
        if not parts:
            conn.send(b'Invalid command')
            with lock:
                fail_count += 1
            return

        command = parts[0].upper()

        if command == 'LIST':
            future = pool.submit(process_task, 'LIST', None)
            result = future.result()
            conn.sendall(result)
            with lock:
                success_count += 1

        elif command == 'UPLOAD':
            if len(parts) < 2:
                conn.send(b'Filename not provided')
                with lock:
                    fail_count += 1
                return
            filename = parts[1]
            conn.send(b'READY')

            # Buat nama file sementara yang unik
            unique_id = str(uuid.uuid4())
            temp_b64_path = os.path.join(FILES_DIR, f"{filename}_{unique_id}.b64")

            with open(temp_b64_path, 'wb') as f:
                while True:
                    chunk = conn.recv(BUFFER_SIZE)
                    if b'__END__' in chunk:
                        f.write(chunk.replace(b'__END__', b''))
                        break
                    f.write(chunk)

            future = pool.submit(process_task, 'UPLOAD_FROM_FILE', (filename, temp_b64_path))
            result = future.result()
            conn.sendall(result)

            if b'successful' in result.lower():
                with lock:
                    success_count += 1
            else:
                with lock:
                    fail_count += 1

        elif command == 'DOWNLOAD':
            if len(parts) < 2:
                conn.send(b'Filename not provided')
                with lock:
                    fail_count += 1
                return
            filename = parts[1]

            future = pool.submit(process_task, 'DOWNLOAD', filename)
            result = future.result()

            if b'file not found' in result.lower():
                conn.sendall(result)
                with lock:
                    fail_count += 1
                return

            for i in range(0, len(result), BUFFER_SIZE):
                conn.sendall(result[i:i+BUFFER_SIZE])
            with lock:
                success_count += 1

        else:
            conn.send(b'Unknown command')
            with lock:
                fail_count += 1

    except Exception as e:
        print(f"[!] Error: {e}")
        try:
            conn.send(f'Error: {e}'.encode())
        except:
            pass
        with lock:
            fail_count += 1
    finally:
        conn.close()

def start_server(num_workers=5):
    status_thread = threading.Thread(target=print_status_periodically, daemon=True)
    status_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(100)
        print(f"[*] Listening di {SERVER_HOST}:{SERVER_PORT} dengan {num_workers} process pool")

        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as pool:
            while True:
                conn, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(conn, addr, pool))
                client_thread.start()

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        workers = int(sys.argv[1])
    else:
        workers = 5
    start_server(workers)
