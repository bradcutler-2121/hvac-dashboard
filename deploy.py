"""Deploy to GitHub Pages - auto-detects username, creates repo, pushes, enables Pages."""
import subprocess
import json
import os
import sys
import urllib.request
import urllib.error
import ssl

GIT = r'C:\Users\b0c0imv\.mingit\cmd\git.exe'
REPO_DIR = r'C:\Users\b0c0imv\Documents\hvac-web'
REPO_NAME = 'hvac-dashboard'
PROXY = 'http://sysproxy.wal-mart.com:8080'

ctx = ssl.create_default_context()


def get_token_gui():
    """Prompt for PAT using a PowerShell input dialog."""
    ps_cmd = '''Add-Type -AssemblyName Microsoft.VisualBasic
$token = [Microsoft.VisualBasic.Interaction]::InputBox(
    "Paste your GitHub Personal Access Token (ghp_...):`n`nThis is used to push the dashboard, then cleared from memory.",
    "GitHub Authentication",
    "")
Write-Output $token'''
    result = subprocess.run(['powershell', '-Command', ps_cmd],
                          capture_output=True, text=True, timeout=120)
    token = result.stdout.strip()
    if not token:
        print('No token provided. Cancelled.', flush=True)
        sys.exit(1)
    return token


def github_api(endpoint, token, method='GET', data=None):
    """Call GitHub API with proxy support."""
    url = f'https://api.github.com{endpoint}'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'hvac-dashboard-deploy',
    }
    if data:
        headers['Content-Type'] = 'application/json'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    proxy_handler = urllib.request.ProxyHandler({'https': PROXY, 'http': PROXY})
    https_handler = urllib.request.HTTPSHandler(context=ctx)
    opener = urllib.request.build_opener(proxy_handler, https_handler)

    try:
        resp = opener.open(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {'error': True, 'status': e.code, 'message': err_body}


def main():
    os.chdir(REPO_DIR)
    os.environ['PATH'] = r'C:\Users\b0c0imv\.mingit\cmd;' + os.environ.get('PATH', '')

    print('Please enter your GitHub PAT in the dialog box...', flush=True)
    token = get_token_gui()

    # Step 1: Get username from token
    print('Checking GitHub identity...', flush=True)
    user = github_api('/user', token)
    if 'error' in user:
        print(f'Token error: {user}', flush=True)
        sys.exit(1)
    username = user['login']
    print(f'  Authenticated as: {username}', flush=True)

    # Step 2: Check if repo exists
    print(f'Checking if {REPO_NAME} repo exists...', flush=True)
    repo = github_api(f'/repos/{username}/{REPO_NAME}', token)
    if 'error' in repo and repo.get('status') == 404:
        # Create it
        print(f'  Creating repo {REPO_NAME}...', flush=True)
        new_repo = github_api('/user/repos', token, method='POST', data={
            'name': REPO_NAME,
            'description': 'HVAC Terminal Summary Dashboard - Feb 9, 2026',
            'public': True,
            'has_issues': False,
            'has_wiki': False,
        })
        if 'error' in new_repo:
            print(f'  Failed to create repo: {new_repo}', flush=True)
            sys.exit(1)
        print(f'  Created: https://github.com/{username}/{REPO_NAME}', flush=True)
    else:
        print(f'  Repo exists: https://github.com/{username}/{REPO_NAME}', flush=True)

    # Step 3: Push
    print('Pushing dashboard files...', flush=True)
    auth_url = f'https://{username}:{token}@github.com/{username}/{REPO_NAME}.git'
    subprocess.run([GIT, 'remote', 'set-url', 'origin', auth_url], check=True,
                   capture_output=True)
    result = subprocess.run([GIT, 'push', '-u', 'origin', 'main'],
                          capture_output=True, text=True)
    # Clear token from remote URL immediately
    subprocess.run([GIT, 'remote', 'set-url', 'origin',
                   f'https://github.com/{username}/{REPO_NAME}.git'],
                   capture_output=True)

    if result.returncode != 0:
        print(f'Push failed: {result.stderr}', flush=True)
        sys.exit(1)
    print('  Pushed successfully!', flush=True)

    # Step 4: Enable GitHub Pages
    print('Enabling GitHub Pages...', flush=True)
    pages = github_api(f'/repos/{username}/{REPO_NAME}/pages', token, method='POST', data={
        'source': {'branch': 'main', 'path': '/'},
        'build_type': 'legacy'
    })
    if 'error' in pages and pages.get('status') == 409:
        print('  Pages already enabled!', flush=True)
    elif 'error' in pages:
        print(f'  Could not auto-enable Pages: {pages.get("message", "unknown")}', flush=True)
        print(f'  Enable manually: https://github.com/{username}/{REPO_NAME}/settings/pages', flush=True)
    else:
        print('  GitHub Pages enabled!', flush=True)

    # Done!
    pages_url = f'https://{username}.github.io/{REPO_NAME}/'
    print(f'\n{"="*60}', flush=True)
    print(f'DASHBOARD IS LIVE!', flush=True)
    print(f'\n  Shareable URL: {pages_url}', flush=True)
    print(f'\n  Share this link with anyone - no VPN or Walmart', flush=True)
    print(f'  network required!', flush=True)
    print(f'{"="*60}', flush=True)

    # Open in browser
    subprocess.Popen([
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        pages_url
    ])


if __name__ == '__main__':
    main()
