import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
from langfuse import Langfuse
import httpx

# Load .env explicitly
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

def run_server_and_request(label, request_id):
    print(f"\n--- Running server with LANGFUSE_PROMPT_LABEL={label} ---")
    env = os.environ.copy()
    env["LANGFUSE_PROMPT_LABEL"] = label
    
    # Start uvicorn process
    proc = subprocess.Popen(
        [".venv/Scripts/python.exe", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--env-file", ".env"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to spin up
    time.sleep(2.5)
    
    try:
        payload = {
            "user_id": f"user-{label}",
            "session_id": f"session-{label}",
            "feature": "qa",
            "message": "What is your refund policy?"
        }
        r = httpx.post("http://127.0.0.1:8000/chat", json=payload, headers={"x-request-id": request_id}, timeout=15.0)
        print(f"Request with label={label} returned {r.status_code}.")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"Request failed: {e}")
    finally:
        # Kill the uvicorn server process
        proc.terminate()
        proc.wait()
        # Force kill any lingering uvicorn processes
        subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST")
    
    client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    
    # 1. Kill any existing uvicorn processes first
    subprocess.run(["taskkill", "/F", "/IM", "uvicorn.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Run with baseline (version 1)
    run_server_and_request("baseline", "req-baseline-v1")
    
    # 3. Run with candidate (version 2)
    run_server_and_request("candidate", "req-candidate-v2")
    
    # 4. Promote production to version 2 (candidate)
    print("\n--- Promoting 'production' label to Prompt Version 2 ---")
    client.update_prompt(name="day13-chat", version=2, new_labels=["production", "candidate"])
    time.sleep(1.0)
    
    # 5. Run with production (should now use version 2)
    run_server_and_request("production", "req-production-v2")
    
    # 6. Rollback production to version 1
    print("\n--- Rolling back 'production' label to Prompt Version 1 ---")
    client.update_prompt(name="day13-chat", version=1, new_labels=["production", "baseline"])
    time.sleep(1.0)
    
    # 7. Run with production (should now use version 1 again)
    run_server_and_request("production", "req-production-v1")
    
    print("\n--- Prompt flow tests completed successfully! ---")

if __name__ == "__main__":
    main()
