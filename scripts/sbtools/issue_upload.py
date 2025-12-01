#!/usr/bin/env python3
"""
scripts/sbtools/issue_upload.py

Python replacement for scripts/sbtools/issueUpload.sh that gathers diagnostic
information and (optionally) uploads it to pastebin. Uses Supervisor's XML-RPC
API to fetch process status and tail logs instead of calling supervisorctl.

Usage:
    - Import and call issue_upload(scoreboard_proc=None, supervisor_url=None)
    - Or run directly: python3 scripts/sbtools/issue_upload.py [procname]

Notes:
    - The script prefers pure-python operations. It still shells out for:
        * git (to get remotes)
        * fastfetch/neofetch (if available, to get a "Host" line)
        * pastebinit (to upload to pastebin)
    - Supervisor XML-RPC URL defaults to http://localhost:9001/RPC2 but can be
      overridden via the supervisor_url argument.

"""

import os
import sys
import subprocess
import datetime
import platform
import shutil
import json
import xmlrpc.client

# You may need to adjust this if your Supervisor is bound to a different host/port.
SUPERVISOR_URL = "http://localhost:9001/RPC2"

def get_git_remotes(root):
    remotes = []
    git_cmd = shutil.which("git")
    if git_cmd:
        try:
            out = subprocess.check_output([git_cmd, "remote", "-v"], cwd=root, text=True)
            remotes = out.strip().split("\n")
        except Exception:
            pass
    return remotes

def get_os_info():
    result = []
    if os.path.isfile('/etc/os-release'):
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        result.append(line.strip().split('=', 1)[1].strip('"'))
                        break
        except Exception:
            pass
    result.append(platform.platform())
    return result

def get_version(root):
    try:
        with open(os.path.join(root, "VERSION")) as f:
            return f.read().strip()
    except Exception:
        return "Unknown"

def fetch_fetch_info():
    fetch_cmd = shutil.which("fastfetch") or shutil.which("neofetch")
    if fetch_cmd:
        args = ["--pipe", "-l", "none"] if "fastfetch" in fetch_cmd else ["--off", "--stdout"]
        try:
            output = subprocess.check_output([fetch_cmd] + args, text=True)
            for line in output.splitlines():
                if "Host" in line:
                    host_line = line.strip()
                    if host_line:
                        return host_line
        except Exception:
            pass  # Fall through to platform info
    else:
        # If fast/neofetch not found, use platform
        uname = platform.uname()
        return f"Host: {uname.node} ({uname.system} {uname.release} {uname.machine})"


def get_venv_info():
    venv_dir = os.path.expanduser("~/nhlsb-venv")
    info = f"{venv_dir} ..... {'FOUND' if os.path.isdir(venv_dir) else 'NOT FOUND'}"
    pip_list = []
    if os.path.isdir(venv_dir):
        pip_cmd = shutil.which("pip")
        if pip_cmd:
            try:
                # Explicitly set VIRTUAL_ENV and PATH for subprocess pip call
                env = os.environ.copy()
                env["VIRTUAL_ENV"] = venv_dir
                env["PATH"] = os.path.join(venv_dir, "bin") + os.pathsep + env.get("PATH", "")
                pip_list = subprocess.check_output([pip_cmd, "list"], text=True, env=env).strip().splitlines()
            except Exception:
                pip_list = ["Could not get pip list"]
        else:
            pip_list = ["pip not found in venv"]
    return info, pip_list

def find_paths():
    paths = [
        ("~/nhl-led-score-board", os.path.expanduser("~/nhl-led-score-board")),
        ("~/nhl-led-scoreboard/submodules/matrix/bindings/python",
         os.path.expanduser("~/nhl-led-scoreboard/submodules/matrix/bindings/python"))
    ]
    out = []
    for label, p in paths:
        found = "..... FOUND" if os.path.isdir(p) else "..... NOT FOUND"
        out.append(f"{label} {found}")
    return out

def redact_config_json(root):
    try:
        config_path = os.path.join(root, "config", "config.json")
        with open(config_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and 'boards' in data and isinstance(data['boards'], dict) and 'weather' in data['boards']:
            if isinstance(data['boards']['weather'], dict):
                data['boards']['weather']['owm_apikey'] = ""
        text = json.dumps(data, indent=2)
        return text
    except Exception as e:
        return f"Could not read config.json: {e}"

def get_scoreboard_log(root):
    log_path = os.path.join(root, "scoreboard.log")
    out = []
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r") as f:
                out = f.read().splitlines()
            os.remove(log_path)
        except Exception:
            out = ["Could not read or delete scoreboard.log"]
    return out

def supervisor_installed(supervisor_url=None):
    url = supervisor_url if supervisor_url else SUPERVISOR_URL
    try:
        proxy = xmlrpc.client.ServerProxy(url)
        # Simple test: getState should work if Supervisor is running and API accessible
        proxy.supervisor.getState()
        return True, proxy
    except Exception:
        return False, None

def supervisor_status(proxy):
    out = []
    try:
        for proc in proxy.supervisor.getAllProcessInfo():
            out.append(f"{proc['name']}: {proc['statename']} ({proc.get('description', '')})")
    except Exception as e:
        out = [f"Could not fetch supervisorctl status: {e}"]
    return out

def supervisor_tail(proxy, proc_name, stream):
    '''
    Read the log file for process `proc_name`, stream is 'stdout' or 'stderr'.
    Only the last 50000 bytes returned, as per the original shell script.
    '''
    try:
        length = 50000
        method = (proxy.supervisor.readProcessStderrLog if stream == "stderr"
                  else proxy.supervisor.readProcessStdoutLog)
        # Attempt to determine logfile path so we can calculate an offset.
        try:
            info = proxy.supervisor.getProcessInfo(proc_name)
            logfile = info['stderr_logfile'] if stream == "stderr" else info['stdout_logfile']
            if logfile and os.path.isfile(logfile):
                size = os.path.getsize(logfile)
                offset = max(0, size - length)
            else:
                offset = 0
        except Exception:
            offset = 0

        output = method(proc_name, offset, length)
        if isinstance(output, bytes):
            output = output.decode(errors='replace')
        return output.splitlines()
    except Exception as e:
        return [f"Could not tail {stream} log: {e}"]

def pastebinit(text):
    pbinit_cmd = shutil.which("pastebinit")
    if not pbinit_cmd:
        return "pastebinit not found!"
    try:
        p = subprocess.run([pbinit_cmd, "-b", "pastebin.com", "-t",
                            "nhl-led-scoreboard issue logs and config"],
                           input=text, text=True, capture_output=True)
        return p.stdout.strip()
    except Exception as e:
        return f"Failed to upload to pastebin: {e}"

def issue_upload(scoreboard_proc=None, supervisor_url=None):
    root = os.path.expanduser("~/nhl-led-scoreboard")
    scoreboard_proc = scoreboard_proc or "scoreboard"
    currdate = datetime.datetime.now().isoformat()
    out = []
    out.append(f"nhl-led-scoreboard issue data {currdate}")
    out.append("=============================")
    out.append("")

    print("Gathering host info...")
    # Host Info
    host_info = fetch_fetch_info()
    version = get_version(root)
    if host_info:
        out.append(f"Running V{version} on a ")
        out.append(host_info)
    else:
        out.append(f"Running V{version} on host:")
        out.append(platform.node())

    # Git Remotes
    print("Gathering git remotes...")
    out.append("------------------------------------------------------")
    out.append("Git Remotes\n=================================")
    out += get_git_remotes(root)

    print("Gathering OS info...")
    out.append("------------------------------------------------------")
    out.append("OS Info\n=================================")
    out += get_os_info()

    out.append("------------------------------------------------------")
    # Venv
    print("Checking for venv and other paths...")
    venv_info, pip_list = get_venv_info()
    out.append(venv_info)
    out += find_paths()

    if os.path.isdir(os.path.expanduser("~/nhlsb-venv")):
        print("Gathering pip list...")
        out.append("------------------------------------------------------")
        out.append("pip list\n=================================")
        out += pip_list

    # config.json
    print("Reading and redacting config.json...")
    out.append("------------------------------------------------------")
    out.append("config.json\n")
    out.append(redact_config_json(root))
    out.append("")

    # scoreboard.log
    print("Reading scoreboard.log...")
    log_contents = get_scoreboard_log(root)
    if log_contents:
        out.append("------------------------------------------------------")
        out.append("scoreboard.log\n=================================")
        out += log_contents

    # Supervisor stuff
    print("Checking for supervisor...")
    supervisor_ok, proxy = supervisor_installed(supervisor_url)

    if supervisor_ok:
        print("Getting supervisor status...")
        out.append("------------------------------------------------------")
        out.append("supervisorctl status\n------------------------------------------------------")
        out += supervisor_status(proxy)
        out.append("------------------------------------------------------")
        print("Getting supervisor stderr log...")
        out.append(f"{scoreboard_proc} stderr log, last 50kb\n=================================")
        out += supervisor_tail(proxy, scoreboard_proc, "stderr")
        out.append("")
        print("Getting supervisor stdout log...")
        out.append("------------------------------------------------------")
        out.append(f"{scoreboard_proc} stdout log, last 50kb\n=================================")
        out += supervisor_tail(proxy, scoreboard_proc, "stdout")
    else:
        out.append("supervisorctl not found or XML-RPC unavailable. Please run the scoreboard with the --logtofile and the --loglevel=DEBUG option to generate a scoreboard.log. Once the issue happens again, rerun this script")

    result = "\n".join(out)
    # Upload if supervisor works
    url = None
    if supervisor_ok:
        print("Uploading to pastebin...")
        url = pastebinit(result)
        print("Take this url and paste it into your issue.  You can create an issue @ https://github.com/falkyre/nhl-led-scoreboard/issues")
        print(url)
    else:
        print(result)
    return url or result

if __name__ == "__main__":
    proc_name = sys.argv[1] if len(sys.argv) > 1 else None
    issue_upload(proc_name)
