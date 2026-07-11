#!/bin/bash
base64 -w 0 /root/bf5e9b794051dac775257e41b7f3bddb.jpg > /tmp/img_b64.txt
echo "{\"image\":\"$(cat /tmp/img_b64.txt)\"}" > /tmp/ocr_request.json
curl -s -X POST http://127.0.0.1:8088/api/baidu-ocr -H "Content-Type: application/json" -d @/tmp/ocr_request.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
rv=d.get('region_values',{})
print('region_values 总数:', len(rv))
for k in ['body_feeling','thinking_spatial','auditory_feeling']:
    print(f'  {k}: {rv.get(k, \"MISSING\")}')
"
