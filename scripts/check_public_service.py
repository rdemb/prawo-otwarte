"""Small operator-triggered live check. Synthetic input only, no retries or outages."""
import argparse
import hashlib
import http.client
import json
import os
import ssl
import time
from urllib.parse import urlsplit

from prawo.settings import public_https_origin


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def connection(origin):
    host = urlsplit(public_https_origin(origin)).hostname
    # HTTPSConnection connects directly; no interception proxy or redirect handler.
    return http.client.HTTPSConnection(host, timeout=40, context=ssl.create_default_context())


def request(origin, path, body=None, method=None, headers=None, expected=200):
    client = connection(origin)
    headers = dict(headers or {})
    raw = None
    if body is not None:
        raw = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    try:
        client.request(method or ('POST' if raw else 'GET'), path, body=raw, headers=headers)
        response = client.getresponse()
        payload = response.read(1_000_001)
        require(len(payload) <= 1_000_000, 'Response exceeds the check size limit')
        require(response.status == expected, f'Unexpected HTTP status on {path}: {response.status}')
        received = {key.lower():value for key,value in response.getheaders()}
        if expected == 204:
            require(not payload, 'Preflight returned a body')
            return None, received
        require('application/json' in received.get('content-type', ''), 'Expected JSON response')
        return json.loads(payload), received
    finally:
        client.close()


def tls_check(origin):
    client = connection(origin)
    try:
        client.connect()
        cert = client.sock.getpeercert()
        remaining = (ssl.cert_time_to_seconds(cert['notAfter']) - time.time()) / 3600
        evidence = {'check':'tls', 'verified':True, 'protocol':client.sock.version(),
                    'sha256':hashlib.sha256(client.sock.getpeercert(binary_form=True)).hexdigest(),
                    'issuer':cert['issuer'], 'san':cert.get('subjectAltName'),
                    'expires':cert['notAfter'], 'remaining_hours':round(remaining,2)}
        print(json.dumps(evidence), flush=True)
        require(remaining >= 48, 'Certificate has less than 48 hours remaining')
    finally:
        client.close()
    data, _ = request(origin, '/healthz')
    require(data.get('status') == 'ok', 'Health endpoint is not OK')
    print(json.dumps({'check':'health','status':'PASS'}), flush=True)


def api_check(origin, pages_url):
    pages = urlsplit(pages_url)
    require(not pages.query and not pages.fragment, 'Pages URL must not contain a query or fragment')
    pages_origin = public_https_origin(f'{pages.scheme}://{pages.netloc}')
    config, _ = request(pages_origin, pages.path.rstrip('/') + '/pages-data.json')
    require(config.get('api_base_url') == origin, 'Published Pages API origin does not match configuration')
    headers = {'Origin':pages_origin}
    status, received = request(origin, '/api/status', headers=headers)
    require(received.get('access-control-allow-origin') == pages_origin, 'Status CORS origin mismatch')
    require(status.get('basal', {}).get('enabled') is True, 'BASAL is not enabled')
    _, received = request(origin, '/api/intake', method='OPTIONS', expected=204, headers={
        **headers, 'Access-Control-Request-Method':'POST', 'Access-Control-Request-Headers':'content-type'})
    require(received.get('access-control-allow-origin') == pages_origin, 'Preflight CORS origin mismatch')
    require('access-control-allow-credentials' not in received, 'Unexpected credentialed CORS')
    require('POST' in received.get('access-control-allow-methods', ''), 'Preflight does not allow POST')
    require('content-type' in received.get('access-control-allow-headers', '').lower(), 'Preflight does not allow JSON')
    description = 'Syntetyczny test działania: otrzymałem decyzję urzędu w sprawie pozwolenia. Chcę uporządkować dokumenty i sprawdzić pouczenie.'
    for domain in ('administrative', 'unknown'):
        started = time.monotonic()
        data, received = request(origin, '/api/intake', {'description':description, 'domain':domain}, headers=headers)
        method = data.get('routing', {}).get('method')
        expected = {'user'} if domain != 'unknown' else {'basal', 'basal_abstained'}
        require(received.get('access-control-allow-origin') == pages_origin, 'Intake CORS origin mismatch')
        require(method in expected, f'Live intake not confirmed: routing method={method}')
        require(data.get('kind') == 'intake_only' and 'legal_answer' in data and data['legal_answer'] is None,
                'Intake must not claim to provide a legal opinion')
        print(json.dumps({'check':'manual_intake' if domain != 'unknown' else 'model_intake',
                          'status':'PASS', 'routing':method, 'elapsed_seconds':round(time.monotonic()-started,3)}), flush=True)
    print(json.dumps({'check':'pages_config_and_cors', 'status':'PASS'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('tls', 'api'), required=True)
    parser.add_argument('--api', default=os.getenv('PRAWO_API_BASE_URL', ''))
    parser.add_argument('--pages-url', default=os.getenv('PRAWO_PAGES_URL', ''))
    args = parser.parse_args()
    origin = public_https_origin(args.api)
    if args.phase == 'tls':
        tls_check(origin)
    else:
        api_check(origin, args.pages_url)
