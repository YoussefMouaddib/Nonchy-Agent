import subprocess
import re
import os
import requests

# Configuration - ONLY CHANGED THE MODEL/API DETAILS
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/deepseek-coder-33b-instruct"
API_KEY = "hf_*********************"  # Your provided key
OPENLANE_DIR = os.path.expanduser("~/OpenLane")

# YOUR EXACT ORIGINAL PROMPT (UNTOUCHED)
PROTOCOL_PROMPT = """
You are a local AI agent. Your job is to interpret user commands into Python function calls.

Protocol:
- If the user says 'synthesize project <design_name>', respond with `run_openlane_synthesis("<design_name>")`
- First think through the request in <think> tags, then provide ONLY the function call after </think>
- It is important that you do not output anything other than one of the available function calls

Example:
User: synthesize project Superscalar-LEGv8
<think>User wants to synthesize project Superscalar-LEGv8</think>
run_openlane_synthesis("Superscalar-LEGv8")

Available functions:
- run_openlane_synthesis(design: str)
"""

def query_ai(prompt: str) -> str:
    """Query HuggingFace API (ONLY changed this function)"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "inputs": PROTOCOL_PROMPT + "\nUser Command:\n" + prompt,
        "parameters": {
            "max_new_tokens": 50,
            "temperature": 0.1  # Keep outputs deterministic
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()[0]['generated_text'].strip()

# EVERYTHING BELOW IS YOUR ORIGINAL CODE (UNCHANGED)
def run_openlane_synthesis(design: str) -> None:
    """Original function - unchanged"""
    print(f"⚡ Running synthesis for {design}...")
    try:
        # Validate design name
        if not re.match(r'^[\w-]+$', design):
            print("❌ Invalid design name")
            return

        # Run commands
        subprocess.run(
            ["make", "mount"],
            cwd=OPENLANE_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        result = subprocess.run(
            f"./flow.tcl -design {design} -tag run -overwrite",
            cwd=OPENLANE_DIR,
            shell=True,
            capture_output=True,
            text=True
        )
        print("📝 Results:\n" + (result.stdout if result.returncode == 0 else result.stderr))
    except Exception as e:
        print(f"⚠️ Error: {str(e)}")

def main():
    print("🧠 OpenLane AI Agent - Ready")
    print("Type 'synthesize project <design_name>' or 'exit'")
    
    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
                
            # Get AI response
            ai_response = query_ai(user_input)
            
            # Parse and execute if valid
            if '</think>' in ai_response:
                func_call = ai_response.split('</think>')[-1].strip()
                print(f"AI: {func_call}")  # Show only the function call
                
                if func_call.startswith('run_openlane_synthesis('):
                    design = re.search(r'\(["\']?(.*?)["\']?\)', func_call).group(1)
                    run_openlane_synthesis(design)
            else:
                print(f"AI: {ai_response}")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"⚠️ System error: {str(e)}")

if __name__ == "__main__":
    main()
