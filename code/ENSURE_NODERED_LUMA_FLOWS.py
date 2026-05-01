import argparse
import json
import sys
import urllib.error
import urllib.request


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(url: str, payload, headers=None):
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=12) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Luma Node-RED flows are loaded")
    parser.add_argument("--base", default="http://127.0.0.1:1880", help="Node-RED base URL")
    parser.add_argument("--flow-file", required=True, help="Path to flow json file")
    parser.add_argument("--min-nodes", type=int, default=11, help="Expected minimum node count")
    args = parser.parse_args()

    try:
        with open(args.flow_file, "r", encoding="utf-8") as f:
            flow_nodes = json.load(f)
    except Exception as ex:
        print(f"[ERROR] Failed reading flow file: {ex}")
        return 2

    try:
        current = get_json(f"{args.base}/flows")
        current_count = len(current)
        print(f"[INFO] Current Node-RED node count: {current_count}")
    except Exception as ex:
        print(f"[ERROR] Failed reading current flows: {ex}")
        return 3

    if current_count >= args.min_nodes:
        print("[OK] Existing flow count already satisfies expected minimum; leaving flows unchanged.")
        return 0

    try:
        status, body = post_json(
            f"{args.base}/flows",
            flow_nodes,
            headers={"Node-RED-API-Version": "v2"},
        )
        print(f"[INFO] POST /flows returned HTTP {status}")
        if body.strip():
            print(f"[INFO] Response: {body[:240]}")
    except urllib.error.HTTPError as ex:
        details = ex.read().decode("utf-8", errors="replace")
        print(f"[ERROR] Flow import failed HTTP {ex.code}: {details[:240]}")
        return 4
    except Exception as ex:
        print(f"[ERROR] Flow import failed: {ex}")
        return 5

    try:
        after = get_json(f"{args.base}/flows")
        after_count = len(after)
        print(f"[INFO] Node count after import: {after_count}")
    except Exception as ex:
        print(f"[ERROR] Could not verify flow count after import: {ex}")
        return 6

    if after_count < args.min_nodes:
        print("[ERROR] Flow import completed but node count is below expected minimum.")
        return 7

    print("[OK] Node-RED flow deployment verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
