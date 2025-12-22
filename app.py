from flask import Flask, render_template, request, jsonify
import subprocess
import datetime
import dns.resolver
import threading
import re

app = Flask(__name__)

# SUBFINDER_BIN = r"C:\Users\TESTING\go\bin\subfinder.exe"
SUBFINDER_BIN = "subfinder"

# --------- GLOBAL PORT SCAN STATE ----------
SCAN_STATE = {
    "running": False,
    "done": False,
    "results": {}
}

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# --------- SUBDOMAIN ENUM ----------
def run_subfinder(domain):
    subs = []
    try:
        result = subprocess.run(
            [SUBFINDER_BIN, "-d", domain, "-silent"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180
        )
        for line in result.stdout.splitlines():
            if line.strip():
                subs.append(line.strip())
    except Exception as e:
        log(f"Subfinder error: {e}")
    return sorted(set(subs))


# --------- DNS → IP ----------
def get_ips(subdomain):
    ips = []
    try:
        answers = dns.resolver.resolve(subdomain, "A", lifetime=3)
        for r in answers:
            ips.append(str(r))
    except:
        pass
    return ips


# --------- NMAP SCAN ----------
def scan_ports(ip):
    open_ports = []
    try:
        result = subprocess.run(
            ["nmap", "-p1-6000", "--open", "-T4", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        for line in result.stdout.splitlines():
            m = re.match(r"(\d+)/tcp\s+open", line)
            if m:
                open_ports.append(m.group(1))
    except Exception as e:
        log(f"Nmap error on {ip}: {e}")

    return open_ports


def background_port_scan(ips):
    SCAN_STATE["running"] = True
    SCAN_STATE["done"] = False
    SCAN_STATE["results"] = {}

    for ip in ips:
        log(f"Scanning ports on {ip}")
        SCAN_STATE["results"][ip] = scan_ports(ip)

    SCAN_STATE["running"] = False
    SCAN_STATE["done"] = True
    log("Port scan completed")


# --------- MAIN PAGE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    domain = ""
    all_subdomains = []
    active_hosts = []
    ip_list = set()

    if request.method == "POST":
        domain = request.form.get("domain", "").strip()
        log(f"Domain submitted: {domain}")

        if domain:
            # 1️⃣ Run subfinder
            all_subdomains = run_subfinder(domain)

            # 2️⃣ Resolve IPs and bind domain → IP
            for sub in all_subdomains:
                ips = get_ips(sub)
                if ips:
                    active_hosts.append({
                        "domain": sub,
                        "ips": ips
                    })
                    for ip in ips:
                        ip_list.add(ip)

    return render_template(
        "index.html",
        domain=domain,
        all_subdomains=all_subdomains,
        active_hosts=active_hosts,
        ip_list=sorted(ip_list),
        scan_running=SCAN_STATE["running"]
    )


# --------- START PORT SCAN ----------
@app.route("/start-port-scan", methods=["POST"])
def start_port_scan():
    ips = request.json.get("ips", [])
    if not ips:
        return jsonify({"error": "No IPs selected"}), 400

    t = threading.Thread(target=background_port_scan, args=(ips,))
    t.start()
    return jsonify({"status": "started"})


# --------- POLL STATUS ----------
@app.route("/port-status")
def port_status():
    return jsonify(SCAN_STATE)


if __name__ == "__main__":
    log("Starting Flask server")
    app.run(debug=False)

