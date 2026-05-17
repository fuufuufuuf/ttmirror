"""Per-account Chrome control: clones the matching system Chrome profile to
``chrome_profile/<account>/Default/`` on first use, runs a dedicated debug Chrome on
``CHROME_DEBUG_PORT``, and dispatches the chrome-devtools MCP skill via ``claude -p``."""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime


# Shadow the built-in print so every line in this module gets a HH:MM:SS prefix
# without having to touch dozens of print() call sites.
_real_print = print
def print(*args, **kwargs):  # noqa: A001 — intentional builtin shadow
    _real_print(f"[{datetime.now().strftime('%H:%M:%S')}]", *args, **kwargs)

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(MODULE_DIR, "skills")
CHROME_ADD_PRODUCT_SKILL_PATH = os.path.join(SKILLS_DIR, "chrome", "tiktok-shop-add-product.md")

CHROME_DEBUG_PORT = 9222
CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_DEFAULT_USER_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
PROJECT_CHROME_PROFILE_DIR = os.path.join(MODULE_DIR, "chrome_profile")


def _chrome_debug_alive() -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{CHROME_DEBUG_PORT}/json/version", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _find_system_chrome_profile_subdir(account: str) -> str:
    """Return the 'Profile X' / 'Default' subfolder under the system Chrome user-data-dir whose
    display name matches the given account (loose match: lowercased, alnum only). '' if none."""
    ls_path = os.path.join(CHROME_DEFAULT_USER_DIR, "Local State")
    if not os.path.isfile(ls_path):
        return ""
    try:
        with open(ls_path) as f:
            ls = json.load(f)
    except Exception:
        return ""
    target = _normalize(account)
    for subdir, info in ls.get("profile", {}).get("info_cache", {}).items():
        if _normalize(info.get("name", "")) == target:
            return subdir
    return ""


def _account_user_data_dir(account: str) -> str:
    return os.path.join(PROJECT_CHROME_PROFILE_DIR, account.strip().lower())


def ensure_chrome_profile_for_account(account: str) -> str:
    """Ensure chrome_profile/<account>/Default is a fresh recursive copy of the matching
    system Chrome profile, so cookies / login state are inherited at copy time.
    Returns the user-data-dir path, or '' if no matching system profile is available.

    Why copy instead of symlink: Chrome's Network Service does not load cookies through a
    Default symlink that escapes the user-data-dir tree (verified on Chrome 147 / macOS:
    Network.getAllCookies returns 0 login cookies even though the symlinked Cookies DB
    contains valid, decryptable session cookies). A real directory copy works.

    Re-copies only when the source Cookies has been modified since the last copy.
    A sidecar marker file (`.src_cookies_mtime`) records the source's mtime AT COPY TIME.
    Comparing against dst's own mtime would be unreliable: the debug Chrome rewrites dst
    Cookies during a run, making dst always newer than src — which would silently block
    re-copy forever even after the user re-logs into system Chrome.

    WARNING: do NOT have system Chrome open with this profile during the copy or while a
    debug Chrome is using the copied profile — system Chrome may rewrite Cookies / Local
    State concurrently. The auto_upload loop pkills its own debug Chrome between runs;
    the user must close (or sign out of) the same account in their main Chrome before
    running auto_upload."""
    user_data = _account_user_data_dir(account)
    profile_dst = os.path.join(user_data, "Default")
    src_subdir = _find_system_chrome_profile_subdir(account)
    if not src_subdir:
        return ""
    src = os.path.join(CHROME_DEFAULT_USER_DIR, src_subdir)
    if not os.path.isdir(src):
        return ""

    src_cookies = os.path.join(src, "Cookies")
    if not os.path.isfile(src_cookies):
        return ""
    marker_path = os.path.join(user_data, ".src_cookies_mtime")
    src_mtime = os.path.getmtime(src_cookies)

    if (os.path.isdir(profile_dst) and not os.path.islink(profile_dst)
            and os.path.isfile(marker_path)):
        try:
            with open(marker_path) as f:
                recorded_mtime = float(f.read().strip())
            if recorded_mtime >= src_mtime:
                return user_data
        except (ValueError, OSError):
            pass  # marker corrupt → fall through to re-copy

    # Guard: refuse to copy while the user's main Chrome is open. Concurrent writes to
    # Cookies / Local State during a copy produce dirty clones whose login state is
    # silently dead — we hit this multiple times before adding this check.
    if subprocess.run(["pgrep", "-x", "Google Chrome"], capture_output=True).returncode == 0:
        print(f"  System Chrome is running; refusing to copy profile for '{account}'. "
              f"Quit Chrome (Cmd+Q) and re-run.")
        return ""

    if os.path.islink(profile_dst):
        os.unlink(profile_dst)
    elif os.path.isdir(profile_dst):
        print(f"  Removing existing {profile_dst} to refresh from system profile…")
        shutil.rmtree(profile_dst)
    os.makedirs(user_data, exist_ok=True)
    print(f"  Copying Chrome profile for '{account}': {src} -> {profile_dst} (may take a while)…")
    shutil.copytree(src, profile_dst, symlinks=True, ignore_dangling_symlinks=True)
    with open(marker_path, "w") as f:
        f.write(f"{src_mtime}\n")
    print(f"  Done copying Chrome profile for '{account}'.")
    return user_data


_current_chrome_account = None


def ensure_debug_chrome(account: str, user_data_dir: str):
    """Make sure a debug Chrome is running on CHROME_DEBUG_PORT with the given account's profile.
    Restarts Chrome if a different account's profile is currently loaded."""
    global _current_chrome_account
    target = account.strip().lower()
    if _chrome_debug_alive() and _current_chrome_account == target:
        return
    if _chrome_debug_alive():
        # NOTE: pattern must NOT start with '--' or pkill on macOS treats it as a flag.
        pattern = f"user-data-dir={PROJECT_CHROME_PROFILE_DIR}"
        subprocess.run(["pkill", "-f", pattern], check=False)
        for _ in range(10):
            time.sleep(0.5)
            if not _chrome_debug_alive():
                break
        if _chrome_debug_alive():
            # SIGTERM was ignored (e.g. long-running / hung Chrome). Escalate.
            subprocess.run(["pkill", "-9", "-f", pattern], check=False)
            for _ in range(10):
                time.sleep(0.5)
                if not _chrome_debug_alive():
                    break
    log_path = "/tmp/chrome_debug.log"
    # Touch the "First Run" sentinel so Chrome treats this profile as already-onboarded.
    # Without it, even with --no-first-run flag, some Chrome builds still show signin/welcome.
    open(os.path.join(user_data_dir, "First Run"), "a").close()

    subprocess.Popen(
        [CHROME_BIN,
         f"--user-data-dir={user_data_dir}",
         "--profile-directory=Default",
         f"--remote-debugging-port={CHROME_DEBUG_PORT}",
         # Suppress first-run / default-browser / EU search-engine choice dialogs that
         # block chrome-devtools MCP from interacting with the actual page.
         "--no-first-run",
         "--no-default-browser-check",
         "--disable-search-engine-choice-screen",
         # Skip auto-downloading multi-GB on-device ML models / heuristics we don't use.
         "--disable-features=OptimizationGuideOnDeviceModel,OptimizationHints,WasmTtsComponentUpdater,SafeBrowsingOnDeviceTailoredSecurity",
         "--disable-component-update"],
        stdout=open(log_path, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(30):
        time.sleep(0.5)
        if _chrome_debug_alive():
            _current_chrome_account = target
            return
    raise RuntimeError(f"Debug Chrome for '{account}' did not become reachable on port {CHROME_DEBUG_PORT} (see {log_path})")


NON_AFFILIATE_NOTE = "此商品不是联盟营销商品。请联系卖家，以将其注册到联盟计划中"
VERIFY_FAILED_PREFIX = "VERIFY_FAILED_PRODUCT_NOT_IN_SHOWCASE:"
# Sentinel value — caller compares chrome_note against this constant to decide whether
# to skip the video entirely (vs. falling back to original-audio upload).
NOT_LOGGED_IN_NOTE = "TikTok Shop 登录态失效，需要重新登录系统 Chrome 对应 profile"

# URL fragments seen when the cloned profile has expired/invalid session and TikTok
# redirects the showcase URL to a generic creator dashboard / login wall.
_LOGIN_REDIRECT_FRAGMENTS = (
    "business.tiktokshop.com/us/creator/live",
    "ttp_session_expire",
    "accounts.tiktok.com/login",
    "seller-us-accounts.tiktok.com/account/register",
)


def _scan_note(text: str, product_id: str) -> str:
    """Map a chunk of skill output to a non-empty note string, or '' if nothing matched."""
    if "NON_AFFILIATE_PRODUCT:" in text:
        return NON_AFFILIATE_NOTE
    if VERIFY_FAILED_PREFIX in text:
        return f"商品 {product_id} 提交后未在橱窗 DOM 中找到，疑似未添加成功"
    if any(frag in text for frag in _LOGIN_REDIRECT_FRAGMENTS):
        return NOT_LOGGED_IN_NOTE
    return ""


def ensure_chrome_action(post_account: str, product_id: str) -> str:
    """After switching the TikTok account, run the Chrome shop dashboard skill if a project profile
    exists (or can be auto-cloned) for that account. Otherwise skip silently.

    Returns:
        ""              — success, OK to proceed with upload.
        NON_AFFILIATE_NOTE — product rejected by TikTok (not in affiliate program); caller should skip upload and mark Feishu.
        any other non-empty string — opaque failure note (chrome action exited non-zero or other unexpected state)."""
    if not post_account:
        return ""
    user_data = ensure_chrome_profile_for_account(post_account)
    if not user_data:
        print(f"  No Chrome profile for '{post_account}' under {PROJECT_CHROME_PROFILE_DIR}; skipping chrome action.")
        return ""
    print(f"  Chrome action for account {post_account} (product_id={product_id})")
    ensure_debug_chrome(post_account, user_data)
    with open(CHROME_ADD_PRODUCT_SKILL_PATH, "r") as f:
        skill_content = f.read()
    prompt = (
        f"Run the chrome-devtools skill below.\n"
        f"PRODUCT_ID: {product_id}\n"
        f"POST_ACCOUNT: {post_account}\n\n"
        f"Execute the steps using the mcp__chrome-devtools__* tools. "
        f"Replace ${{PRODUCT_ID}} and ${{POST_ACCOUNT}} with the values above.\n\n"
        f"--- SKILL ---\n{skill_content}\n--- END SKILL ---"
    )
    proc = subprocess.Popen(
        ["claude", "-p", "--model", "claude-haiku-4-5-20251001",
         "--verbose", "--output-format", "stream-json",
         "--allowedTools", "mcp__chrome-devtools__*", "Bash"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd=MODULE_DIR,
        text=True,
        bufsize=1,
    )
    proc.stdin.write(prompt)
    proc.stdin.close()

    note = ""
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text"):
                    text = block["text"]
                    print(f"  {text}", flush=True)
                    if not note:
                        note = _scan_note(text, product_id)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = json.dumps(block.get("input", {}), ensure_ascii=False)
                    print(f"  -> {name}({inp})", flush=True)
        elif etype == "tool_result":
            content = event.get("content", "")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "text":
                        text = c.get("text", "")
                        print(f"     = {text[:200]}", flush=True)
                        if not note:
                            note = _scan_note(text, product_id)
        elif etype == "result":
            text = str(event.get("result", ""))
            print(f"  Result: {text[:300]}", flush=True)
            if not note:
                note = _scan_note(text, product_id)

    proc.wait()
    if proc.returncode != 0:
        print(f"  Warning: chrome action exited {proc.returncode}", file=sys.stderr)
        if not note:
            note = f"chrome action exit {proc.returncode}"
    return note
