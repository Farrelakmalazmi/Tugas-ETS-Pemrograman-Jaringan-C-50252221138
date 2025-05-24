import socket
import os
import base64
import concurrent.futures
import sys
import threading
import time

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8889
BUFFER_SIZE = 1024
FILES_DIR = 'server_files'

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

# Variabel global untuk tracking sukses/gagal worker
success_count = 0
fail_count = 0
lock = threading.Lock()

def handle_client(conn, addr):
    global success_count, fail_count
    print(f"[+] Menangani koneksi dari {addr}")
    try:
        data = conn.recv(BUFFER_SIZE).decode()
        if not data:
            with lock:
                fail_count += 1
            conn.close()
            return

        parts = data.strip().split()
        if not parts:
            conn.send(b'Invalid command')
            with lock:
                fail_count += 1
            return

        command = parts[0].upper()

        if command == 'LIST':
            files = os.listdir(FILES_DIR)
            response = '\n'.join(files) if files else 'No files found.'
            conn.send(response.encode())
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

            received = b''
            while True:
                chunk = conn.recv(BUFFER_SIZE)
                if b'__END__' in chunk:
                    received += chunk.replace(b'__END__', b'')
                    break
                received += chunk

            try:
                decoded_data = base64.b64decode(received)
                filepath = os.path.join(FILES_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(decoded_data)
                conn.send(b'Upload successful')
                with lock:
                    success_count += 1
            except Exception as e:
                conn.send(f'Error during upload: {str(e)}'.encode())
                with lock:
                    fail_count += 1

        elif command == 'DOWNLOAD':
            if len(parts) < 2:
                conn.send(b'Filename not provided')
                with lock:
                    fail_count += 1
                return
            filename = parts[1]
            filepath = os.path.join(FILES_DIR, filename)

            if not os.path.exists(filepath):
                conn.send(b'File not found')
                with lock:
                    fail_count += 1
                return

            with open(filepath, 'rb') as f:
                file_data = f.read()
                encoded = base64.b64encode(file_data)
                for i in range(0, len(encoded), BUFFER_SIZE):
                    conn.send(encoded[i:i+BUFFER_SIZE])
                conn.send(b'__END__')
            with lock:
                success_count += 1

        else:
            conn.send(b'Unknown command')
            with lock:
                fail_count += 1

    except Exception as e:
        print(f"[!] Error with client {addr}: {e}")
        try:
            conn.send(f'Error: {e}'.encode())
        except:
            pass
        with lock:
            fail_count += 1
    finally:
        conn.close()

def print_status_periodically():
    global success_count, fail_count
    while True:
        time.sleep(10)
        with lock:
            print(f"[Server Status] Success count: {success_count}, Fail count: {fail_count}")

def start_server(num_workers=5):
    status_thread = threading.Thread(target=print_status_periodically, daemon=True)
    status_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(100)
        print(f"[*] Listening di {SERVER_HOST}:{SERVER_PORT} dengan {num_workers} thread pool")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            while True:
                conn, addr = server_socket.accept()
                executor.submit(handle_client, conn, addr)

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        workers = int(sys.argv[1])
    else:
        workers = 5
    start_server(workers)
