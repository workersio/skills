#!/usr/bin/env python3

#author: skshadan

import argparse
import requests
import json
import sys
import time
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock, Semaphore
from datetime import datetime
from pathlib import Path
from queue import Queue
import threading

def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

class Logger:
    def __init__(self, no_color=False):
        self.no_color = no_color
    
    def _c(self, color, text):
        if self.no_color:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def info(self, msg):
        print(f"{self._c(Colors.CYAN, '[*]')} {msg}")
    
    def success(self, msg):
        print(f"{self._c(Colors.GREEN, '[+]')} {msg}")
    
    def warning(self, msg):
        print(f"{self._c(Colors.YELLOW, '[-]')} {msg}")
    
    def error(self, msg):
        print(f"{self._c(Colors.RED, '[ERROR]')} {msg}")
    
    def action(self, msg):
        print(f"{self._c(Colors.WHITE, '[>]')} {msg}")
    
    def scan(self, msg):
        print(f"{self._c(Colors.BLUE, '[SCAN]')} {msg}")
    
    def secret(self, msg):
        print(f"{self._c(Colors.RED + Colors.BOLD, '[SECRET]')} {msg}")
    
    def clean(self, msg):
        print(f"{self._c(Colors.GREEN, '[CLEAN]')} {msg}")
    
    def retry(self, msg):
        print(f"{self._c(Colors.YELLOW, '[RETRY]')} {msg}")

log = Logger()
write_lock = Lock()
rate_limiter = Semaphore(1)

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GitMail-Finder"
}

if GITHUB_TOKEN and GITHUB_TOKEN != "ghp_xxxx":
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

REQUEST_DELAY = 2 if not GITHUB_TOKEN or GITHUB_TOKEN == "ghp_xxxx" else 0.5
MAX_RETRIES = 3
RETRY_DELAY = 60

BANNER = """
   _____ _ _   __  __       _ _ 
  / ____(_) | |  \\/  |     (_) |
 | |  __ _| |_| \\  / | __ _ _| |
 | | |_ | | __| |\\/| |/ _` | | |
 | |__| | | |_| |  | | (_| | | |
  \\_____|_|\\__|_|  |_|\\__,_|_|_|
                                
  GitHub Email OSINT + Secret Scanner by skshadan
"""

def print_banner():
    print(f"{Colors.CYAN}{BANNER}{Colors.RESET}")

def get_github_username(email: str) -> dict | None:
    url = f"{GITHUB_API}/search/commits?q=author-email:{email}"
    
    for attempt in range(MAX_RETRIES):
        try:
            with rate_limiter:
                time.sleep(REQUEST_DELAY)
                response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 403:
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_time = int(reset_time) - int(time.time()) + 5
                    if wait_time > 0 and wait_time < 300:
                        log.warning(f"Rate limited. Waiting {wait_time}s for {email}")
                        time.sleep(wait_time)
                        continue
                
                if attempt < MAX_RETRIES - 1:
                    log.warning(f"Rate limited for {email}. Retry {attempt + 1}/{MAX_RETRIES} in {RETRY_DELAY}s")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    log.error(f"Rate limit exceeded for {email}")
                    return None
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get("total_count", 0) == 0 or not data.get("items"):
                return None
            
            author = data["items"][0].get("author")
            if author and author.get("login"):
                return {
                    "email": email,
                    "username": author["login"],
                    "profile": f"https://github.com/{author['login']}"
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            log.error(f"Request failed for {email}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
                continue
            return None
        except json.JSONDecodeError:
            log.error(f"Invalid JSON response for {email}")
            return None
    
    return None

def get_user_repos(username: str, skip_forks: bool = False) -> list:
    repos = []
    page = 1
    
    log.action(f"Fetching repos for user: {username}...")
    
    while True:
        url = f"{GITHUB_API}/users/{username}/repos?per_page=100&page={page}"
        
        try:
            with rate_limiter:
                time.sleep(REQUEST_DELAY / 2)
                response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 403:
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_time = int(reset_time) - int(time.time()) + 5
                    if wait_time > 0 and wait_time < 300:
                        log.warning(f"Rate limited fetching repos. Waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue
                break
            
            if response.status_code != 200:
                break
            
            data = response.json()
            
            if not data:
                break
            
            for repo in data:
                if skip_forks and repo.get("fork", False):
                    continue
                    
                repos.append({
                    "name": repo.get("name"),
                    "url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url"),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "fork": repo.get("fork", False)
                })
            
            # Show progress every 5 pages
            if page % 5 == 0:
                print(f"\r[*] Fetched {len(repos)} repos (page {page})...", end="", flush=True)
            
            page += 1
            
            if len(data) < 100:
                break
                
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to fetch repos for {username}: {e}")
            break
    
    if repos:
        print(f"\r[+] Fetched {len(repos)} repos for {username}" + " " * 20)
    return repos

def get_org_repos(org: str, skip_forks: bool = False) -> list:
    """Get all repositories for a GitHub organization"""
    repos = []
    page = 1
    
    log.action(f"Fetching repos for org: {org}...")
    
    while True:
        url = f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}"
        
        try:
            with rate_limiter:
                time.sleep(REQUEST_DELAY / 2)
                response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 403:
                reset_time = response.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_time = int(reset_time) - int(time.time()) + 5
                    if wait_time > 0 and wait_time < 300:
                        log.warning(f"Rate limited fetching org repos. Waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue
                break
            
            if response.status_code == 404:
                log.error(f"Organization not found: {org}")
                return []
            
            if response.status_code != 200:
                log.error(f"Failed to fetch org repos: {response.status_code}")
                break
            
            data = response.json()
            
            if not data:
                break
            
            for repo in data:
                if skip_forks and repo.get("fork", False):
                    continue
                    
                repos.append({
                    "name": repo.get("name"),
                    "url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url"),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "fork": repo.get("fork", False)
                })
            
            # Show progress every 5 pages (500 repos)
            if page % 5 == 0:
                print(f"\r[*] Fetched {len(repos)} repos (page {page})...", end="", flush=True)
            
            page += 1
            
            if len(data) < 100:
                break
                
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to fetch repos for org {org}: {e}")
            break
    
    log.success(f"Found {len(repos)} repos for org {org}")
    return repos

def process_username(username: str, skip_forks: bool = False) -> dict | None:
    """Process a direct username input"""
    log.action(f"Fetching repos for user: {username}...")
    
    url = f"{GITHUB_API}/users/{username}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 404:
            log.error(f"User not found: {username}")
            return None
        
        if response.status_code != 200:
            log.error(f"Failed to fetch user: {response.status_code}")
            return None
        
        user_data = response.json()
        
        result = {
            "email": user_data.get("email", "N/A"),
            "username": username,
            "profile": f"https://github.com/{username}",
            "repos": get_user_repos(username, skip_forks)
        }
        
        log.success(f"Found {len(result['repos'])} repos for {username}")
        return result
        
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch user {username}: {e}")
        return None

def process_org(org: str, skip_forks: bool = False) -> dict | None:
    """Process an organization input"""
    repos = get_org_repos(org, skip_forks)
    
    if not repos:
        return None
    
    return {
        "email": "N/A",
        "username": org,
        "profile": f"https://github.com/{org}",
        "repos": repos,
        "is_org": True
    }

def process_email(email: str, fetch_repos: bool, skip_forks: bool = False) -> dict | None:
    email = email.strip()
    
    if not email or email.startswith("#"):
        return None
    
    log.action(f"Searching: {email}")
    
    result = get_github_username(email)
    
    if result:
        log.success(f"Found: {result['username']} ({email})")
        
        if fetch_repos:
            log.action(f"Fetching repos for {result['username']}...")
            result["repos"] = get_user_repos(result["username"], skip_forks)
            log.success(f"Found {len(result['repos'])} repos")
        
        return result
    else:
        log.warning(f"No GitHub account found for {email}")
    
    return None

def load_emails_from_file(filepath: str) -> list:
    emails = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "|" in line:
                        line = line.split("|")[-1].strip()
                    emails.append(line)
        
        log.info(f"Loaded {len(emails)} emails from {filepath}")
        return emails
        
    except FileNotFoundError:
        log.error(f"File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error reading file: {e}")
        sys.exit(1)

def load_usernames_from_file(filepath: str) -> list:
    usernames = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "|" in line:
                        line = line.split("|")[-1].strip()
                    usernames.append(line)
        
        log.info(f"Loaded {len(usernames)} usernames from {filepath}")
        return usernames
        
    except FileNotFoundError:
        log.error(f"File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error reading file: {e}")
        sys.exit(1)

def load_orgs_from_file(filepath: str) -> list:
    orgs = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "|" in line:
                        line = line.split("|")[-1].strip()
                    orgs.append(line)
        
        log.info(f"Loaded {len(orgs)} organizations from {filepath}")
        return orgs
        
    except FileNotFoundError:
        log.error(f"File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Error reading file: {e}")
        sys.exit(1)

def scan_repo(repo_info: tuple, verified: bool = True, timeout: int = 300) -> dict:
    """Scan a single repo with TruffleHog using git mode (faster, no API limits)"""
    idx, total, repo_name, repo_url, username, email = repo_info
    
    result = {
        "repo": repo_name,
        "url": repo_url,
        "username": username,
        "email": email,
        "secrets": [],
        "error": None,
        "status": "clean"
    }
    
    trufflehog_path = "/opt/homebrew/bin/trufflehog"
    if not os.path.exists(trufflehog_path):
        trufflehog_path = "trufflehog"
    
    cmd = [trufflehog_path, "git", repo_url, "--json", "--no-update"]
    
    if verified:
        cmd.append("--results=verified")
    
    for attempt in range(2):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "NO_COLOR": "1"}
            )
            
            if proc.stdout:
                for line in proc.stdout.strip().split('\n'):
                    if line:
                        try:
                            finding = json.loads(line)
                            if "DetectorName" not in finding:
                                continue
                            
                            git_meta = finding.get("SourceMetadata", {}).get("Data", {}).get("Git", {})
                            
                            file_path = git_meta.get("file", "Unknown")
                            line_num = git_meta.get("line", "")
                            commit_hash = git_meta.get("commit", "")[:8]
                            
                            if commit_hash and file_path != "Unknown":
                                file_link = f"{repo_url}/blob/{commit_hash}/{file_path}"
                                if line_num:
                                    file_link += f"#L{line_num}"
                            else:
                                file_link = repo_url
                            
                            secret_info = {
                                "detector": finding.get("DetectorName", "Unknown"),
                                "verified": finding.get("Verified", False),
                                "raw": finding.get("Redacted", "")[:50],
                                "file": file_path,
                                "line": line_num,
                                "commit": commit_hash,
                                "file_link": file_link,
                                "repo": repo_name,
                                "repo_url": repo_url,
                                "username": username,
                                "email": email
                            }
                            result["secrets"].append(secret_info)

                        except json.JSONDecodeError:
                            continue
            
            if result["secrets"]:
                result["status"] = "secrets_found"
            
            return result
            
        except subprocess.TimeoutExpired:
            if attempt == 0:
                continue
            result["error"] = f"Timeout after {timeout}s"
            result["status"] = "timeout"
            return result
            
        except FileNotFoundError:
            result["error"] = "TruffleHog not found. Install: brew install trufflehog"
            result["status"] = "error"
            return result
            
        except Exception as e:
            if attempt == 0:
                time.sleep(5)
                continue
            result["error"] = str(e)
            result["status"] = "error"
            return result
    
    return result

def run_scans_parallel(email_or_user_input, scan_threads: int, verified: bool, timeout: int, output_file: str = None, skip_forks: bool = False, is_email_list: bool = False, is_username: bool = False, is_org: bool = False, is_user_list: bool = False, is_org_list: bool = False):
    """Run parallel fetching and scanning - fetch repos and scan simultaneously"""
    
    repo_queue = Queue()
    scan_results = []
    total_secrets = 0
    completed = 0
    total_repos = 0
    secrets_by_user = {}
    all_findings = []
    results_lock = Lock()
    
    output_data = {
        "scan_date": datetime.now().isoformat(),
        "emails_scanned": 0,
        "accounts_found": 0,
        "repos_scanned": 0,
        "total_secrets": 0,
        "scan_status": "in_progress",
        "findings": []
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    scanning_active = threading.Event()
    scanning_active.set()
    
    def scan_worker():
        """Worker that continuously scans repos from the queue"""
        nonlocal completed, total_secrets
        
        while scanning_active.is_set() or not repo_queue.empty():
            try:
                repo_info = repo_queue.get(timeout=1)
            except:
                continue
            
            if repo_info is None:
                break

            result = scan_repo(repo_info, verified, timeout)
            
            with results_lock:
                completed += 1
                scan_results.append(result)
                
                if result["status"] == "secrets_found":
                    for secret in result["secrets"]:
                        log.secret(f"{result['repo']} | {secret['detector']} | {secret['raw']}... | {'Verified' if secret['verified'] else 'Unverified'}")
                        total_secrets += 1
                        
                        finding = {
                            "email": result["email"],
                            "username": result["username"],
                            "repo": result["repo"],
                            "repo_url": result["url"],
                            "detector": secret["detector"],
                            "verified": secret["verified"],
                            "file": secret["file"],
                            "line": secret["line"],
                            "commit": secret["commit"],
                            "file_link": secret["file_link"],
                            "raw_redacted": secret["raw"]
                        }
                        all_findings.append(finding)
                        
                        if output_file:
                            output_data["findings"] = all_findings
                            output_data["total_secrets"] = total_secrets
                            output_data["repos_scanned"] = completed
                            with open(output_file, 'w') as f:
                                json.dump(output_data, f, indent=2)
                    
                    if result["username"] not in secrets_by_user:
                        secrets_by_user[result["username"]] = {"repos": 0, "secrets": 0}
                    secrets_by_user[result["username"]]["repos"] += 1
                    secrets_by_user[result["username"]]["secrets"] += len(result["secrets"])
                    
                elif result["status"] == "clean":
                    log.clean(f"{result['repo']} | No secrets found")
                    
                elif result["status"] == "timeout":
                    log.error(f"[{completed}/{total_repos}] {result['repo']} | Timeout, skipping")
                    
                elif result["status"] == "error":
                    log.error(f"[{completed}/{total_repos}] {result['repo']} | {result['error']}")
                
                if total_repos > 0 and (completed % 10 == 0 or completed == total_repos):
                    pct = int((completed / total_repos) * 100)
                    bar_filled = int(pct / 5)
                    bar = '█' * bar_filled + '░' * (20 - bar_filled)
                    print(f"\r{Colors.CYAN}[*] Progress: [{bar}] {pct}% ({completed}/{total_repos}){Colors.RESET}", end='', flush=True)
            
            repo_queue.task_done()
    
    log.info("Starting parallel fetch and scan")
    log.info(f"Scan threads: {scan_threads} | Verified only: {verified}")

    if output_file:
        log.info(f"Results will be saved to: {output_file}")
    
    print()
    
    scan_workers = []
    for _ in range(scan_threads):
        worker = threading.Thread(target=scan_worker, daemon=True)
        worker.start()
        scan_workers.append(worker)
    
    results = []
    repo_counter = 0
    
    if is_username:
        # Stream repos to queue as they're fetched
        username = email_or_user_input
        log.action(f"Fetching repos for user: {username}...")
        page = 1
        user_repos = []
        
        while True:
            url = f"{GITHUB_API}/users/{username}/repos?per_page=100&page={page}"
            
            try:
                with rate_limiter:
                    time.sleep(REQUEST_DELAY / 2)
                    response = requests.get(url, headers=HEADERS, timeout=30)
                
                if response.status_code == 403:
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        wait_time = int(reset_time) - int(time.time()) + 5
                        if wait_time > 0 and wait_time < 300:
                            log.warning(f"Rate limited. Waiting {wait_time}s")
                            time.sleep(wait_time)
                            continue
                    break
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                
                if not data:
                    break
                
                for repo in data:
                    if skip_forks and repo.get("fork", False):
                        continue
                    
                    repo_info = {
                        "name": repo.get("name"),
                        "url": repo.get("html_url"),
                        "clone_url": repo.get("clone_url"),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "fork": repo.get("fork", False)
                    }
                    user_repos.append(repo_info)
                    
                    # Add to queue immediately!
                    repo_counter += 1
                    total_repos = repo_counter
                    repo_queue.put((repo_counter, 0, repo_info["name"], repo_info["url"], username, "N/A"))
                
                if page % 5 == 0:
                    print(f"\r[*] Fetched {len(user_repos)} repos, {repo_counter} queued for scan (page {page})...", end="", flush=True)
                
                page += 1
                
                if len(data) < 100:
                    break
                    
            except requests.exceptions.RequestException as e:
                log.error(f"Failed to fetch repos: {e}")
                break
        
        if user_repos:
            print(f"\r[+] Fetched {len(user_repos)} repos, all queued for scanning" + " " * 20)
            results.append({
                "email": "N/A",
                "username": username,
                "profile": f"https://github.com/{username}",
                "repos": user_repos
            })
    
    elif is_org:
        # Stream repos to queue as they're fetched
        org = email_or_user_input
        log.action(f"Fetching repos for org: {org}...")
        page = 1
        org_repos = []
        
        while True:
            url = f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}"
            
            try:
                with rate_limiter:
                    time.sleep(REQUEST_DELAY / 2)
                    response = requests.get(url, headers=HEADERS, timeout=30)
                
                if response.status_code == 403:
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        wait_time = int(reset_time) - int(time.time()) + 5
                        if wait_time > 0 and wait_time < 300:
                            log.warning(f"Rate limited. Waiting {wait_time}s")
                            time.sleep(wait_time)
                            continue
                    break
                
                if response.status_code == 404:
                    log.error(f"Organization not found: {org}")
                    break
                
                if response.status_code != 200:
                    log.error(f"Failed to fetch org repos: {response.status_code}")
                    break
                
                data = response.json()
                
                if not data:
                    break
                
                for repo in data:
                    if skip_forks and repo.get("fork", False):
                        continue
                    
                    repo_info = {
                        "name": repo.get("name"),
                        "url": repo.get("html_url"),
                        "clone_url": repo.get("clone_url"),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "fork": repo.get("fork", False)
                    }
                    org_repos.append(repo_info)
                    
                    # Add to queue immediately!
                    repo_counter += 1
                    total_repos = repo_counter
                    repo_queue.put((repo_counter, 0, repo_info["name"], repo_info["url"], org, "N/A"))
                
                if page % 5 == 0:
                    print(f"\r[*] Fetched {len(org_repos)} repos, {repo_counter} queued for scan (page {page})...", end="", flush=True)
                
                page += 1
                
                if len(data) < 100:
                    break
                    
            except requests.exceptions.RequestException as e:
                log.error(f"Failed to fetch repos: {e}")
                break
        
        if org_repos:
            print(f"\r[+] Fetched {len(org_repos)} repos, all queued for scanning" + " " * 20)
            results.append({
                "email": "N/A",
                "username": org,
                "profile": f"https://github.com/{org}",
                "repos": org_repos,
                "is_org": True
            })
    
    elif is_user_list:
        usernames = email_or_user_input if isinstance(email_or_user_input, list) else [email_or_user_input]
        
        output_data["users_scanned"] = len(usernames)
        
        def fetch_and_queue_user(username):
            nonlocal repo_counter, total_repos
            result = process_username(username, skip_forks)
            if result:
                with results_lock:
                    results.append(result)
                    for repo in result.get("repos", []):
                        repo_counter += 1
                        total_repos = repo_counter
                        repo_queue.put((repo_counter, 0, repo["name"], repo["url"], result["username"], result.get("email", "N/A")))
            return result
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_and_queue_user, username): username for username in usernames}
            for future in as_completed(futures):
                future.result()
    
    elif is_org_list:
        orgs = email_or_user_input if isinstance(email_or_user_input, list) else [email_or_user_input]
        
        output_data["orgs_scanned"] = len(orgs)
        
        def fetch_and_queue_org(org):
            nonlocal repo_counter, total_repos
            result = process_org(org, skip_forks)
            if result:
                with results_lock:
                    results.append(result)
                    for repo in result.get("repos", []):
                        repo_counter += 1
                        total_repos = repo_counter
                        repo_queue.put((repo_counter, 0, repo["name"], repo["url"], result["username"], result.get("email", "N/A")))
            return result
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_and_queue_org, org): org for org in orgs}
            for future in as_completed(futures):
                future.result()
    
    elif is_email_list:
        emails = email_or_user_input if isinstance(email_or_user_input, list) else [email_or_user_input]
        
        output_data["emails_scanned"] = len(emails)
        
        def fetch_and_queue(email):
            nonlocal repo_counter, total_repos
            result = process_email(email, True, skip_forks)
            if result:
                with results_lock:
                    results.append(result)
                    for repo in result.get("repos", []):
                        repo_counter += 1
                        total_repos = repo_counter
                        repo_queue.put((repo_counter, 0, repo["name"], repo["url"], result["username"], result["email"]))
            return result
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_and_queue, email): email for email in emails}
            for future in as_completed(futures):
                future.result()
    
    with results_lock:
        for repo_info_idx in range(repo_counter):
            if repo_info_idx < len(scan_results):
                continue
    
    for i in range(repo_counter):
        idx = i + 1
        for result_item in [r for r in scan_results if r]:
            pass
    
    repo_queue.join()
    
    scanning_active.clear()
    
    for worker in scan_workers:
        worker.join(timeout=2)
    
    print()
    print()
    log.info("Scan complete!")
    print()
    
    output_data["accounts_found"] = len(results)
    output_data["repos_scanned"] = completed
    
    print(f"{Colors.BOLD}RESULTS SUMMARY{Colors.RESET}")
    print("-" * 50)
    print(f"{'Username':<20} {'Repos':<10} {'Secrets Found':<15}")
    print("-" * 50)
    
    for user_result in results:
        username = user_result["username"]
        repo_count = len(user_result.get("repos", []))
        secret_count = secrets_by_user.get(username, {}).get("secrets", 0)
        
        if secret_count > 0:
            print(f"{Colors.RED}{username:<20} {repo_count:<10} {secret_count:<15}{Colors.RESET}")
        else:
            print(f"{username:<20} {repo_count:<10} {secret_count:<15}")
    
    print("-" * 50)
    print(f"{Colors.BOLD}Total: {total_secrets} secrets in {completed} repos{Colors.RESET}")
    print()
    
    if output_file:
        output_data["total_secrets"] = total_secrets
        output_data["scan_status"] = "completed"
        output_data["findings"] = all_findings
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        log.success(f"Output saved: {output_file}")

def run_scans(results: list, scan_threads: int, verified: bool, timeout: int, output_file: str = None):
    """Run TruffleHog scans on all repos using git mode"""
    
    all_repos = []
    for user_result in results:
        if user_result.get("repos"):
            for repo in user_result["repos"]:
                all_repos.append((
                    len(all_repos) + 1,
                    0,
                    repo["name"],
                    repo["url"],
                    user_result["username"],
                    user_result["email"]
                ))
    
    if not all_repos:
        log.warning("No repos to scan")
        return
    
    for i, repo in enumerate(all_repos):
        all_repos[i] = (repo[0], len(all_repos), repo[2], repo[3], repo[4], repo[5])
    
    log.info(f"Starting TruffleHog scan on {len(all_repos)} repos")
    log.info(f"Scan threads: {scan_threads} | Verified only: {verified}")

    if output_file:
        log.info(f"Results will be saved to: {output_file}")
    
    print()
    
    scan_results = []
    total_secrets = 0
    completed = 0
    
    secrets_by_user = {}
    all_findings = []
    
    output_data = {
        "scan_date": datetime.now().isoformat(),
        "emails_scanned": len(results),
        "accounts_found": len([r for r in results if r]),
        "repos_scanned": len(all_repos),
        "total_secrets": 0,
        "scan_status": "in_progress",
        "findings": []
    }
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    with ProcessPoolExecutor(max_workers=scan_threads) as executor:
        futures = {executor.submit(scan_repo, repo, verified, timeout): repo for repo in all_repos}
        
        for future in as_completed(futures):
            repo_info = futures[future]
            completed += 1
            
            try:
                result = future.result()
                scan_results.append(result)
                
                if result["status"] == "secrets_found":
                    for secret in result["secrets"]:
                        log.secret(f"{result['repo']} | {secret['detector']} | {secret['raw']}... | {'Verified' if secret['verified'] else 'Unverified'}")
                        total_secrets += 1
                        
                        finding = {
                            "email": result["email"],
                            "username": result["username"],
                            "repo": result["repo"],
                            "repo_url": result["url"],
                            "detector": secret["detector"],
                            "verified": secret["verified"],
                            "file": secret["file"],
                            "line": secret["line"],
                            "commit": secret["commit"],
                            "file_link": secret["file_link"],
                            "raw_redacted": secret["raw"]
                        }
                        all_findings.append(finding)
                        
                        if output_file:
                            with write_lock:
                                output_data["findings"] = all_findings
                                output_data["total_secrets"] = total_secrets
                                with open(output_file, 'w') as f:
                                    json.dump(output_data, f, indent=2)
                    
                    if result["username"] not in secrets_by_user:
                        secrets_by_user[result["username"]] = {"repos": 0, "secrets": 0}
                    secrets_by_user[result["username"]]["repos"] += 1
                    secrets_by_user[result["username"]]["secrets"] += len(result["secrets"])
                    
                elif result["status"] == "clean":
                    log.clean(f"{result['repo']} | No secrets found")
                    
                elif result["status"] == "timeout":
                    log.error(f"[{completed}/{len(all_repos)}] {result['repo']} | Timeout, skipping")
                    
                elif result["status"] == "error":
                    log.error(f"[{completed}/{len(all_repos)}] {result['repo']} | {result['error']}")
                
                if completed % 10 == 0 or completed == len(all_repos):
                    pct = int((completed / len(all_repos)) * 100)
                    bar_filled = int(pct / 5)
                    bar = '█' * bar_filled + '░' * (20 - bar_filled)
                    print(f"\r{Colors.CYAN}[*] Progress: [{bar}] {pct}% ({completed}/{len(all_repos)}){Colors.RESET}", end='', flush=True)
                    
            except Exception as e:
                log.error(f"Scan failed for {repo_info[2]}: {e}")
    
    print()
    print()
    log.info("Scan complete!")
    print()
    
    print(f"{Colors.BOLD}RESULTS SUMMARY{Colors.RESET}")
    print("-" * 50)
    print(f"{'Username':<20} {'Repos':<10} {'Secrets Found':<15}")
    print("-" * 50)
    
    for user_result in results:
        username = user_result["username"]
        repo_count = len(user_result.get("repos", []))
        secret_count = secrets_by_user.get(username, {}).get("secrets", 0)
        
        if secret_count > 0:
            print(f"{Colors.RED}{username:<20} {repo_count:<10} {secret_count:<15}{Colors.RESET}")
        else:
            print(f"{username:<20} {repo_count:<10} {secret_count:<15}")
    
    print("-" * 50)
    print(f"{Colors.BOLD}Total: {total_secrets} secrets in {len(all_repos)} repos{Colors.RESET}")
    print()
    
    if output_file:
        output_data["total_secrets"] = total_secrets
        output_data["scan_status"] = "completed"
        output_data["findings"] = all_findings
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        log.success(f"Output saved: {output_file}")

def write_output(results: list, output_file: str, fetch_repos: bool):
    with open(output_file, 'w') as f:
        for result in results:
            f.write(f"Email: {result['email']}\n")
            f.write(f"Username: {result['username']}\n")
            f.write(f"Profile: {result['profile']}\n")
            
            if fetch_repos and result.get("repos"):
                f.write(f"Repositories ({len(result['repos'])}):\n")
                for repo in result["repos"]:
                    f.write(f"  {repo['name']}: {repo['url']}\n")
            
            f.write("\n")
    
    log.success(f"Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Email OSINT + Secret Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--list", dest="email_list", help="Path to file containing email list")
    group.add_argument("-m", "--mail", dest="single_mail", help="Single email address to lookup")
    group.add_argument("-u", "--user", dest="username", help="Direct GitHub username")
    group.add_argument("-U", "--user-list", dest="user_list", help="Path to file containing username list")
    group.add_argument("-O", "--org", dest="org_name", help="GitHub organization name")
    group.add_argument("-L", "--org-list", dest="org_list", help="Path to file containing organization list")
    
    parser.add_argument("-o", "--output", dest="output_file", help="Output file path")
    parser.add_argument("-r", "--repos", action="store_true", help="Fetch all repositories for found users")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Number of threads for email lookup (default: 1)")
    parser.add_argument("-d", "--delay", type=float, default=None, help="Delay between requests in seconds")
    
    parser.add_argument("-s", "--scan", action="store_true", help="Enable TruffleHog secret scanning")
    parser.add_argument("-st", "--scan-threads", type=int, default=10, help="Parallel scan workers (default: 10)")
    parser.add_argument("--verified-only", action="store_true", help="Only show verified secrets (faster)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-repo scan timeout in seconds (default: 300)")
    parser.add_argument("--skip-forks", action="store_true", help="Skip forked repositories")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()
    
    global log, REQUEST_DELAY
    log = Logger(no_color=args.no_color)
    
    if args.delay is not None:
        REQUEST_DELAY = args.delay
    
    print_banner()
    
    if args.scan and not args.repos:
        args.repos = True
        log.info("Scan enabled, automatically fetching repos")
    
    results = []
    
    if args.username:
        log.info(f"Processing username: {args.username}")
        print()
        if args.scan:
            verified = args.verified_only
            run_scans_parallel(
                args.username,
                args.scan_threads,
                verified,
                args.timeout,
                args.output_file,
                args.skip_forks,
                is_username=True
            )
        else:
            result = process_username(args.username, args.skip_forks)
            if result:
                results.append(result)
    
    elif args.user_list:
        usernames = load_usernames_from_file(args.user_list)
        
        if not usernames:
            log.error("No usernames to process")
            sys.exit(1)
        
        log.info(f"Processing {len(usernames)} username(s)")
        print()
        
        if args.scan:
            verified = args.verified_only
            run_scans_parallel(
                usernames,
                args.scan_threads,
                verified,
                args.timeout,
                args.output_file,
                args.skip_forks,
                is_user_list=True
            )
        else:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {executor.submit(process_username, username, args.skip_forks): username for username in usernames}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
            
            print()
            log.info(f"Username scan complete: {len(results)} accounts from {len(usernames)} usernames")
            print()
    
    elif args.org_name:
        log.info(f"Processing organization: {args.org_name}")
        print()
        if args.scan:
            verified = args.verified_only
            run_scans_parallel(
                args.org_name,
                args.scan_threads,
                verified,
                args.timeout,
                args.output_file,
                args.skip_forks,
                is_org=True
            )
        else:
            result = process_org(args.org_name, args.skip_forks)
            if result:
                results.append(result)
    
    elif args.org_list:
        orgs = load_orgs_from_file(args.org_list)
        
        if not orgs:
            log.error("No organizations to process")
            sys.exit(1)
        
        log.info(f"Processing {len(orgs)} organization(s)")
        print()
        
        if args.scan:
            verified = args.verified_only
            run_scans_parallel(
                orgs,
                args.scan_threads,
                verified,
                args.timeout,
                args.output_file,
                args.skip_forks,
                is_org_list=True
            )
        else:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {executor.submit(process_org, org, args.skip_forks): org for org in orgs}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
            
            print()
            log.info(f"Organization scan complete: {len(results)} accounts from {len(orgs)} organizations")
            print()
    
    elif args.single_mail or args.email_list:
        emails = []
        
        if args.single_mail:
            emails = [args.single_mail]
        elif args.email_list:
            emails = load_emails_from_file(args.email_list)
        
        if not emails:
            log.error("No emails to process")
            sys.exit(1)
        
        log.info(f"Processing {len(emails)} email(s) with {args.threads} thread(s)")
        
        if GITHUB_TOKEN and GITHUB_TOKEN != "ghp_xxxx":
            log.success("GitHub token detected")
        else:
            log.warning("No GITHUB_TOKEN set. Rate limit: 10 requests/min")
            log.info("Set GITHUB_TOKEN in .env for higher limits")
        
        print()
        
        if args.scan:
            verified = args.verified_only
            run_scans_parallel(
                emails,
                args.scan_threads,
                verified,
                args.timeout,
                args.output_file,
                args.skip_forks,
                is_email_list=True
            )
        else:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {executor.submit(process_email, email, args.repos, args.skip_forks): email for email in emails}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
            
            print()
            log.info(f"Email scan complete: {len(results)} accounts from {len(emails)} emails")
            print()
    
    if args.output_file and results and not args.scan:
        write_output(results, args.output_file, args.repos)
    
    if not results and not args.scan:
        log.warning("No GitHub accounts found")

if __name__ == "__main__":
    main()