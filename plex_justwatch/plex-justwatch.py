"""  Copyright 2019 Esri
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
   http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License. """

from flask import Flask, request
import os
import json
from utils import PlexJustWatchPlaylistManager

app = Flask(__name__)
manager = PlexJustWatchPlaylistManager()

@app.route('/', methods=['POST','GET', 'PUT', 'PATCH'])
def index():
    payload = request.form.get('payload')
    if payload:
        data = json.loads(request.form.get('payload'))
        manager.process_event(data)
        return f"PLEX DATA: {data}"
    if request.method == 'GET':
        return '<h1>Hello from Webhook Listener!</h1>'
    if request.method == 'POST':
        req_data = request.get_json()
        str_obj = json.dumps(req_data)
        return '{"success":"true"}'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)