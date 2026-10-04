"""Minimal Anthropic Messages API mock. Logs every request body; scripted replies."""
import json, sys, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
LOG = os.environ.get("MOCK_LOG", "/tmp/mock_requests.jsonl")
SCRIPT = os.environ.get("MOCK_SCRIPT", "")  # "agent:router-fast" -> first main request returns an Agent tool call
state = {"agent_sent": False}

def sse(h, ev, data):
    h.wfile.write(f"event: {ev}\ndata: {json.dumps(data)}\n\n".encode()); h.wfile.flush()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("content-type","application/json"); self.end_headers(); self.wfile.write(b'{"data":[]}')
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("content-length", 0)) or 0)
        try: req = json.loads(body)
        except Exception: req = {}
        with open(LOG, "a") as f: f.write(json.dumps({"path": self.path, "req": req}) + "\n")
        if "count_tokens" in self.path:
            return self._json({"input_tokens": 100})
        if not self.path.startswith("/v1/messages"):
            return self._json({})
        tools = [t.get("name") for t in req.get("tools", []) if isinstance(t, dict)]
        agent_tool = next((t for t in ("Agent", "Task") if t in tools), None)
        content = [{"type": "text", "text": "ok"}]; stop = "end_turn"
        if SCRIPT.startswith("agent:") and agent_tool and not state["agent_sent"] and "router" in json.dumps(req.get("messages", []))[-4000:]:
            state["agent_sent"] = True
            content = [{"type": "tool_use", "id": "toolu_01", "name": agent_tool,
                        "input": {"description": "rename", "prompt": "rename foo to bar in a.ts", "subagent_type": SCRIPT.split(":",1)[1]}}]
            stop = "tool_use"
        sys_txt = json.dumps(req.get("system", ""))
        if not tools and ("should be blocked" in sys_txt or "severity" in json.dumps(req.get("messages", []))[-600:]):
            content = [{"type": "text", "text": "<severity>0</severity>"}]
        model = req.get("model", "claude-sonnet")
        if req.get("stream"):
            self.send_response(200); self.send_header("content-type", "text/event-stream"); self.end_headers()
            sse(self, "message_start", {"type":"message_start","message":{"id":"msg_1","type":"message","role":"assistant","model":model,"content":[],"stop_reason":None,"usage":{"input_tokens":10,"output_tokens":1}}})
            for i, c in enumerate(content):
                if c["type"] == "text":
                    sse(self, "content_block_start", {"type":"content_block_start","index":i,"content_block":{"type":"text","text":""}})
                    sse(self, "content_block_delta", {"type":"content_block_delta","index":i,"delta":{"type":"text_delta","text":c["text"]}})
                else:
                    sse(self, "content_block_start", {"type":"content_block_start","index":i,"content_block":{"type":"tool_use","id":c["id"],"name":c["name"],"input":{}}})
                    sse(self, "content_block_delta", {"type":"content_block_delta","index":i,"delta":{"type":"input_json_delta","partial_json":json.dumps(c["input"])}})
                sse(self, "content_block_stop", {"type":"content_block_stop","index":i})
            sse(self, "message_delta", {"type":"message_delta","delta":{"stop_reason":stop,"stop_sequence":None},"usage":{"output_tokens":5}})
            sse(self, "message_stop", {"type":"message_stop"})
        else:
            self._json({"id":"msg_1","type":"message","role":"assistant","model":model,"content":content,"stop_reason":stop,"usage":{"input_tokens":10,"output_tokens":5}})
    def _json(self, o):
        b = json.dumps(o).encode(); self.send_response(200); self.send_header("content-type","application/json"); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)

ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8787), H).serve_forever()
