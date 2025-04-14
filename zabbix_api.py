import requests
import json
from datetime import datetime
import time
import logging

# Konfigurasi Logging
logging.basicConfig(
    filename="zabbix_api.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Konfigurasi Zabbix API
ZABBIX_URL = ""
ZABBIX_API_TOKEN = ""

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ZABBIX_API_TOKEN}"
}

def call_api(payload):
    """
    Mengirim permintaan ke Zabbix API dan mengembalikan hasilnya.
    """
    try:
        response = requests.post(ZABBIX_URL, headers=HEADERS, data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            logging.error(f"Zabbix API Error: {result['error']}")
            raise Exception(f"Zabbix API Error: {result['error']}")
        logging.debug(f"API call successful: {payload['method']}")
        return result["result"]
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return None

def get_active_high_problems(severity=4):
    """
    Mengambil masalah aktif dengan severity tertentu dari Zabbix.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "problem.get",
        "params": {
            "output": ["eventid", "name", "severity", "clock"],
            "selectAcknowledges": ["message", "clock"],
            "selectTags": ["tag", "value"],
            "sortfield": "eventid",
            "sortorder": "DESC",
            "filter": {
                "severity": severity
            }
        },
        "id": 1
    }
    result = call_api(payload)
    if result is None:
        logging.warning(f"No problems retrieved for severity {severity}")
    else:
        logging.info(f"Retrieved {len(result)} problems with severity {severity}")
    return result

def get_host_by_event(eventid):
    """
    Mengambil nama host berdasarkan event ID.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "event.get",
        "params": {
            "output": ["eventid"],
            "selectHosts": ["name"],
            "eventids": eventid
        },
        "id": 2
    }
    result = call_api(payload)
    if result and len(result) > 0 and "hosts" in result[0] and result[0]["hosts"]:
        host_name = result[0]["hosts"][0]["name"]
        logging.debug(f"Host found for eventid {eventid}: {host_name}")
        return host_name
    logging.warning(f"No host found for eventid: {eventid}")
    return "Unknown"

def format_duration(seconds):
    """
    Mengonversi detik ke format Xh Ym Zs.
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    result = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    logging.debug(f"Formatted duration {seconds}s to '{result}'")
    return result

def fetch_zabbix_data(severity=4):
    """
    Mengambil data masalah dari Zabbix dan mengembalikan DataFrame.
    """
    problems = get_active_high_problems(severity)
    if not problems:
        logging.error(f"Failed to fetch problems from Zabbix API for severity {severity}")
        return None
    
    now = int(time.time())
    data = []
    for p in problems:
        time_str = datetime.fromtimestamp(int(p["clock"])).strftime("%Y-%m-%d %H:%M:%S")
        duration_seconds = now - int(p["clock"])
        duration = format_duration(duration_seconds)
        host = get_host_by_event(p["eventid"])
        tags = p.get("tags", [])
        tags_str = ", ".join(f"{t['tag']}:{t['value']}" for t in tags) or "None"
        ack_msg = p["acknowledges"][0]["message"] if p.get("acknowledges") else "N/A"
        
        logging.debug(f"EventID: {p['eventid']}, Host: {host}, Problem: {p['name']}, Tags: {tags_str}")
        
        data.append({
            "Time": time_str,
            "Severity": p["severity"],
            "Host": host,
            "Status": "PROBLEM",
            "Duration": duration,
            "Problem": p["name"],
            "Ack Message": ack_msg,
            "Tags": tags_str,
            "EventID": p["eventid"]
        })
    
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        if df.empty:
            logging.warning("No problems found after processing")
        else:
            logging.info(f"Fetched {len(df)} problems from API")
        return df
    except ImportError:
        logging.error("Pandas not installed, cannot create DataFrame")
        return None

if __name__ == "__main__":
    print("Menarik data problem severity HIGH yang belum resolved...")
    problems = get_active_high_problems()
    if problems:
        print(f"{'Time':<20} {'Severity':<10} {'Host':<25} {'Problem':<40} {'Duration':<15} {'Ack Message':<25} {'Tags':<30}")
        print("-" * 170)
        now = int(time.time())
        for p in problems:
            time_str = datetime.fromtimestamp(int(p["clock"])).strftime("%Y-%m-%d %H:%M:%S")
            duration = format_duration(now - int(p["clock"]))
            severity = p["severity"]
            host = get_host_by_event(p["eventid"])
            problem_name = p["name"]
            ack_msg = p["acknowledges"][0]["message"] if p.get("acknowledges") else "N/A"
            tags = ", ".join(f"{t['tag']}:{t['value']}" for t in p.get("tags", [])) or "None"

            print(f"{time_str:<20} {severity:<10} {host[:23]+'...' if len(host) > 23 else host:<25} "
                  f"{problem_name[:38]+'...' if len(problem_name) > 38 else problem_name:<40} "
                  f"{duration:<15} "
                  f"{ack_msg[:23]+'...' if len(ack_msg) > 23 else ack_msg:<25} "
                  f"{tags[:28]+'...' if len(tags) > 28 else tags:<30}")
    else:
        print("Tidak ada problem aktif dengan severity High.")