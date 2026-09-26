import json, subprocess, sys
voice = sys.argv[1] if len(sys.argv) > 1 else 'en_US-lessac-high'
for L in json.load(open('/vo/lines.json')):
    subprocess.run(['piper', '-m', f'/voices/{voice}.onnx', '--length_scale', '1.02', '--sentence_silence', '0.25',
                    '-f', f'/vo/{L["id"]}.wav'], input=L['text'].replace('—', ',').encode(), check=True, capture_output=True)
    print('ok', L['id'])
