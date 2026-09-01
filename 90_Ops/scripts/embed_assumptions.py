#!/usr/bin/env python3
from pathlib import Path
from datetime import date
import json
v=Path(__file__).resolve().parent.parent.parent; p=v/"90_Ops"/"_status"/"runs";p.mkdir(parents=True,exist_ok=True);print(json.dumps({"status":"noop","date":str(date.today())}))
