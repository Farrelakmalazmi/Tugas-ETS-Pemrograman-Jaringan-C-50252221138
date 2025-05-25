import socket
import os
import base64
import concurrent.futures
import time
import sys
from tqdm import tqdm  # pastikan sudah install tqdm dengan `pip install tqdm`

SERVER_HOST = '172.16.16.101'  # Ganti sesuai IP server sebenarnya
SERVER_PORT = 8995
BUFFER_SIZE = 1048576   # 16 KB buffer
CLIENT_DIR = 'client_files'
DOWNLOAD_DIR = 'client_downloads'

# Pastikan folder unduhan ada
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def upload_file(filename):
    try:
        filepath = os.path.join(CLIENT_DIR, filename)
        filesize = os.path.getsize(filepath)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.send(f'UPLOAD {filename}'.encode())

            response = s.recv(BUFFER_SIZE)
            if response != b'READY':
                return False, f"Server not ready: {response.decode()}"

            with open(filepath, 'rb') as f, tqdm(total=filesize, unit='B', unit_scale=True, desc=f'Upload {filename}', leave=False) as pbar:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    encoded_chunk = base64.b64encode(chunk)
                    s.send(encoded_chunk)
                    pbar.update(len(chunk))

            s.send(b'__END__')

            result = s.recv(BUFFER_SIZE).decode()
            return True, result
    except Exception as e:
        return False, str(e)

def download_file(filename):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.send(f'DOWNLOAD {filename}'.encode())

            data = b''
            filesize = None  # kalau bisa dapat info filesize, tapi di protokol ini belum ada
            with tqdm(unit='B', unit_scale=True, desc=f'Download {filename}', leave=False) as pbar:
                while True:
                    part = s.recv(BUFFER_SIZE)
                    if b'__END__' in part:
                        data += part.replace(b'__END__', b'')
                        pbar.update(len(part) - len(b'__END__'))
                        break
                    data += part
                    pbar.update(len(part))

            decoded = base64.b64decode(data)
            with open(os.path.join(DOWNLOAD_DIR, filename), 'wb') as f:
                f.write(decoded)

            return True, "Download success"
    except Exception as e:
        return False, str(e)

def worker_task(operation, filename):
    start = time.time()
    if operation == 'upload':
        success, msg = upload_file(filename)
    elif operation == 'download':
        success, msg = download_file(filename)
    else:
        return False, 0, 0, f"Invalid operation: {operation}"
    end = time.time()

    time_used = end - start
    # Hitung size file berdasarkan operasi
    path = os.path.join(CLIENT_DIR if operation == 'upload' else DOWNLOAD_DIR, filename)
    size = os.path.getsize(path) if success and os.path.exists(path) else 0
    throughput = size / time_used if time_used > 0 else 0
    return success, time_used, throughput, msg

def main():
    if len(sys.argv) != 5:
        print("Usage: python3 client_pool.py [upload/download] [10MB|50MB|100MB] [num_workers] [thread|process]")
        return

    operation = sys.argv[1].lower()
    volume = sys.argv[2]
    num_workers = int(sys.argv[3])
    mode = sys.argv[4].lower()

    volume_to_file = {
        "10MB": "test_10mb.txt",
        "50MB": "test_50mb.txt",
        "100MB": "test_100mb.txt"
    }

    filename = volume_to_file.get(volume, None)
    if filename is None:
        print(f"Volume {volume} tidak dikenali")
        return

    if mode == 'thread':
        Executor = concurrent.futures.ThreadPoolExecutor
    elif mode == 'process':
        Executor = concurrent.futures.ProcessPoolExecutor
    else:
        print("Mode harus 'thread' atau 'process'")
        return

    print(f"Starting stress test: {operation} {filename} | Workers: {num_workers} | Mode: {mode}")

    success_count = 0
    fail_count = 0
    total_time = 0
    total_throughput = 0

    with Executor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_task, operation, filename) for _ in range(num_workers)]
        for future in concurrent.futures.as_completed(futures):
            success, time_used, throughput, msg = future.result()
            if success:
                success_count += 1
                total_time += time_used
                total_throughput += throughput
            else:
                fail_count += 1
            print(f"[{'OK' if success else 'FAIL'}] Time: {time_used:.2f}s | Throughput: {throughput:.2f} B/s | Msg: {msg}")

    avg_time = total_time / success_count if success_count else 0
    avg_throughput = total_throughput / success_count if success_count else 0

    print("--- Summary ---")
    print(f"Operation         : {operation.upper()}")
    print(f"File              : {filename}")
    print(f"Workers           : {num_workers}")
    print(f"Mode              : {mode}")
    print(f"Average time      : {avg_time:.2f} s")
    print(f"Average throughput: {avg_throughput:.2f} B/s")
    print(f"Success count     : {success_count}")
    print(f"Fail count        : {fail_count}")

if __name__ == '__main__':
    main()
