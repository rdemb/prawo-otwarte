"""Bounded, content-free loopback gateway for a dedicated llama-server child.

One admitted request is held until the upstream finishes, including after client
disconnect. Upstream failure kills and reaps the child before freeing admission.
No request text, response text, URL or exception details are logged.
"""
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import subprocess
import threading
import time


class Runtime:
    def __init__(self, command, port, timeout):
        self.command, self.port, self.timeout = command, port, timeout
        self.lock = threading.BoundedSemaphore(1)
        self.process_lock = threading.Lock()
        self.process = None
        self.start()
        threading.Thread(target=self.watch, daemon=True).start()

    def watch(self):
        while True:
            time.sleep(1)
            if self.process.poll() is not None and self.lock.acquire(blocking=False):
                try:
                    if self.process.poll() is not None:
                        self.restart()
                finally:
                    self.lock.release()

    def start(self):
        with self.process_lock:
            self.process = subprocess.Popen(self.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def restart(self):
        with self.process_lock:
            self.process.kill()
            self.process.wait(timeout=10)
            self.process = subprocess.Popen(self.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def call(self, path, body=None, timeout=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=timeout or self.timeout)
        try:
            conn.request('POST' if body is not None else 'GET', path, body=body,
                         headers={'Content-Type': 'application/json'})
            r = conn.getresponse()
            data = r.read(100001)
            if len(data) > 100000:
                raise ValueError('response limit')
            return r.status, data
        finally:
            conn.close()


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 4

    def __init__(self, address, runtime, model):
        self.runtime, self.model = runtime, model
        self.handlers = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.handlers.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.handlers.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.handlers.release()

    def handle_error(self, request, address):
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = 'LocalGenerator'

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self.reply(code, b'{"error":"invalid_request"}')

    def reply(self, code, data):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            pass

    def do_GET(self):
        if self.path != '/health':
            return self.reply(404, b'{"error":"not_found"}')
        try:
            status, _ = self.server.runtime.call('/health', timeout=1)
            self.reply(status, b'{"status":"ok"}' if status == 200 else b'{"status":"loading"}')
        except (OSError, http.client.HTTPException, ValueError):
            self.reply(503, b'{"status":"unavailable"}')

    def do_POST(self):
        if self.path != '/v1/chat/completions':
            return self.reply(404, b'{"error":"not_found"}')
        runtime = self.server.runtime
        if not runtime.lock.acquire(blocking=False):
            return self.reply(503, b'{"error":"generator_busy"}')
        try:
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < length <= 100000:
                    raise ValueError()
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError()
                data = json.loads(raw)
                if set(data) != {'model','temperature','max_tokens','stream','response_format','messages'}:
                    raise ValueError()
                if data['model'] != self.server.model or data['stream'] is not False or data['temperature'] != 0 or type(data['max_tokens']) is not int or not 1 <= data['max_tokens'] <= 700:
                    raise ValueError()
                messages = data['messages']
                if len(messages) != 2 or [m['role'] for m in messages] != ['system','user'] or any(set(m) != {'role','content'} or not isinstance(m['content'],str) for m in messages):
                    raise ValueError()
                if sum(len(m['content']) for m in messages) > 35000:
                    raise ValueError()
                if data['response_format'].get('type') != 'json_object' or not isinstance(data['response_format'].get('schema'), dict):
                    raise ValueError()
            except (ValueError, KeyError, TypeError, AttributeError, OSError):
                return self.reply(400, b'{"error":"invalid_request"}')
            try:
                code, result = runtime.call('/v1/chat/completions', raw)
                self.reply(code, result if code == 200 else b'{"error":"generation_failed"}')
            except (OSError, http.client.HTTPException, ValueError):
                # A timed-out connection is not evidence that computation stopped.
                # Reap the dedicated runtime before another request can be admitted.
                runtime.restart()
                self.reply(503, b'{"error":"generation_failed"}')
        finally:
            runtime.lock.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--upstream-port', type=int, default=8768)
    parser.add_argument('--timeout', type=float, default=115)
    parser.add_argument('--model', default='bielik')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not 1 <= args.timeout <= 120 or args.port == args.upstream_port:
        parser.error('Expected dedicated runtime command, distinct ports and bounded timeout')
    runtime = Runtime(command, args.upstream_port, args.timeout)
    Gateway(('127.0.0.1', args.port), runtime, args.model).serve_forever()


if __name__ == '__main__':
    main()
