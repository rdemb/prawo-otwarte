import http.client
import json
import socket
import threading
import unittest

from deploy.generator_gateway import Gateway


class ControlledRuntime:
    def __init__(self):
        self.lock = threading.BoundedSemaphore(1)
        self.entered = threading.Event()
        self.finish = threading.Event()
        self.restarted = threading.Event()
        self.fail = False

    def call(self, path, body=None, timeout=None):
        if path == '/health':
            return 200, b'{}'
        self.entered.set()
        if not self.finish.wait(5):
            raise RuntimeError('test failed to release runtime')
        if self.fail:
            raise TimeoutError()
        return 200, b'{"choices":[]}'

    def restart(self):
        # Admission must remain occupied while termination/reaping happens.
        assert not self.lock.acquire(blocking=False)
        self.restarted.set()


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ControlledRuntime()
        self.server = Gateway(('127.0.0.1',0), self.runtime, 'bielik')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.payload = {'model':'bielik','temperature':0,'max_tokens':700,'stream':False,
                        'response_format':{'type':'json_object','schema':{'type':'object'}},
                        'messages':[{'role':'system','content':'Synthetic test.'},
                                    {'role':'user','content':'SYNTHETIC_PRIVATE_523'}]}

    def close(self):
        self.runtime.finish.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, payload=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        connection.request('POST','/v1/chat/completions',json.dumps(payload or self.payload),
                           {'Content-Type':'application/json'})
        response = connection.getresponse()
        data = response.read()
        connection.close()
        return response.status, data

    def test_disconnect_keeps_admission_until_actual_completion(self):
        body = json.dumps(self.payload).encode()
        connection = socket.create_connection(self.server.server_address)
        connection.sendall(b'POST /v1/chat/completions HTTP/1.0\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)
        self.assertTrue(self.runtime.entered.wait(2))
        connection.close()
        self.assertEqual(self.request()[0],503)
        self.runtime.finish.set()
        # Synchronize on the actual semaphore, rather than an arbitrary sleep.
        self.assertTrue(self.runtime.lock.acquire(timeout=2))
        self.runtime.lock.release()
        self.assertEqual(self.request()[0],200)

    def test_upstream_timeout_reaps_child_before_releasing_admission(self):
        self.runtime.fail = True
        self.runtime.finish.set()
        self.assertEqual(self.request()[0],503)
        self.assertTrue(self.runtime.restarted.is_set())
        self.assertTrue(self.runtime.lock.acquire(timeout=2))
        self.runtime.lock.release()

    def test_rejects_tools_history_streaming_and_unbounded_output(self):
        for change in [{'tools':[]},{'stream':True},{'max_tokens':701},{'model':'other'},
                       {'messages':[{'role':'user','content':'test'}]},
                       {'messages':[{'role':'system','content':[]},{'role':'user','content':'test'}]}]:
            with self.subTest(change=change):
                self.assertEqual(self.request(dict(self.payload,**change))[0],400)
                self.assertFalse(self.runtime.entered.is_set())
