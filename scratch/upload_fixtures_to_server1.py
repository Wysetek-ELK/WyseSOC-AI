import urllib.request, json

# 1. Login
auth_req = urllib.request.Request(
    'http://172.26.41.240/api/auth/login',
    data=json.dumps({'username': 'admin', 'password': 'AdminPassword123!'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
token = json.loads(urllib.request.urlopen(auth_req).read().decode('utf-8'))['access_token']
print('[+] Authenticated on Server 1')

# 2. Upload fixtures zip
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
with open('fixtures/Incident json.zip', 'rb') as f:
    zip_bytes = f.read()

parts = [
    f'--{boundary}\r\n'.encode('utf-8'),
    b'Content-Disposition: form-data; name="file"; filename="Incident_json.zip"\r\n',
    b'Content-Type: application/zip\r\n\r\n',
    zip_bytes,
    f'\r\n--{boundary}--\r\n'.encode('utf-8')
]
body = b''.join(parts)

upload_req = urllib.request.Request(
    'http://172.26.41.240/api/imports/upload',
    data=body,
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }
)

try:
    resp = json.loads(urllib.request.urlopen(upload_req, timeout=60).read().decode('utf-8'))
    print('[+] Import completed on Server 1:')
    print('    Job ID:', resp.get('job_id'))
    print('    Status:', resp.get('status'))
    print('    Total found:', resp.get('total_found'))
    print('    Rules detected:', resp.get('rules_detected'))
    print('    Imported:', resp.get('imported'))
    print('    Duplicates:', resp.get('duplicates'))
    print('    Errors:', resp.get('errors'))
    if resp.get('error_messages'):
        print('    Error details:', resp.get('error_messages'))
except Exception as e:
    print('[-] Import failed:', e)
