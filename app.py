from flask import Flask, render_template, request, jsonify
import subprocess
import dns.resolver
import threading
import re

app = Flask(__name__)

# ---------------- GLOBAL SCAN STATE ----------------
SCAN_STATE = {
    "running": False,
    "done": False,
    "ports": {}
}

# ---------------- SUBDOMAIN ENUM ----------------
def run_sublist3r(domain):
    subs = []
    try:
        result = subprocess.run(
            ["sublist3r", "-d", domain, "-n"],
            capture_output=True,
            text=True,
            timeout=180
        )

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.endswith(domain):
                subs.append(line)

    except Exception as e:
        print("Sublist3r error:", e)

    return sorted(set(subs))


# ---------------- DNS + IP ----------------
def get_dns_info(subdomain):
    ips = []
    active = False

    for rtype in ["A", "AAAA"]:
        try:
            for r in dns.resolver.resolve(subdomain, rtype):
                ips.append(str(r))
                active = True
        except:
            pass

    try:
        dns.resolver.resolve(subdomain, "CNAME")
        active = True
    except:
        pass

    return active, sorted(set(ips))


# ---------------- NMAP PORT SCAN ----------------
def nmap_scan(ip):
    """
    Fast full TCP scan using Nmap
    """
    open_ports = []

    try:
        cmd = [
            "nmap",
            "-p1-6000",          
            "-sS",               
            "-T4",               
            "--min-rate", "3000",
            "--open",
            ip
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        for line in result.stdout.splitlines():
            # Example: 80/tcp open http
            match = re.match(r"(\d+)/tcp\s+open", line)
            if match:
                open_ports.append(int(match.group(1)))

    except Exception as e:
        print(f"Nmap error on {ip}:", e)

    return sorted(open_ports)


# ---------------- BACKGROUND SCAN ----------------
def full_port_scan(ips):
    SCAN_STATE["running"] = True
    SCAN_STATE["done"] = False
    SCAN_STATE["ports"] = {}

    for ip in ips:
        SCAN_STATE["ports"][ip] = []
        SCAN_STATE["ports"][ip] = nmap_scan(ip)

    SCAN_STATE["running"] = False
    SCAN_STATE["done"] = True


# ---------------- MAIN PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    domain = ""
    all_subs = []
    active_subs = []
    ip_map = {}
    all_ips = []

    if request.method == "POST":
        domain = request.form.get("domain", "")
        all_subs = run_sublist3r(domain)

        ip_set = set()

        for sub in all_subs:
            active, ips = get_dns_info(sub)
            if active:
                active_subs.append(sub)
                if ips:
                    ip_map[sub] = ips
                    for ip in ips:
                        ip_set.add(ip)

        all_ips = list(ip_set)

    return render_template(
        "index.html",
        domain=domain,
        all_subs=all_subs,
        active_subs=active_subs,
        ip_map=ip_map,
        all_ips=all_ips
    )


# ---------------- START PORT SCAN ----------------
@app.route("/start-port-scan", methods=["POST"])
def start_port_scan():
    ips = request.json.get("ips", [])
    t = threading.Thread(target=full_port_scan, args=(ips,))
    t.start()
    return jsonify({"status": "started"})


# ---------------- POLL PORT SCAN ----------------
@app.route("/port-status")
def port_status():
    return jsonify(SCAN_STATE)
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
