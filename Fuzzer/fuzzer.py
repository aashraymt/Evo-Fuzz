import requests
import random
import string
import time
import json

# CONFIGURATION
TARGET_URL = "http://localhost:5000/api/process-data"
SEED_PAYLOAD = "A" * 10  # A valid baseline string
MAX_VARIANTS = 2000      # How many mutations to try

def banner():
    print("""
    =============================================
      SERVICE-FUZZ: API Variant Hunter
      Targeting: C# .NET Core Web Services
    =============================================
    """)

# STEP 1: OBSERVE (Generate Variants)
def mutate_payload(seed):
    """
    Applies random bit-flipping, expansion, and edge-case injection.
    """
    strategy = random.choice(['expand', 'shrink', 'bitflip', 'edgecase'])
    
    if strategy == 'expand':
        # Rapidly expand buffer size to trigger overflows
        return seed * random.randint(2, 10)
    
    elif strategy == 'shrink':
        return seed[:random.randint(0, len(seed))]
    
    elif strategy == 'bitflip':
        # Simulate data corruption
        char_list = list(seed)
        if char_list:
            char_list[random.randint(0, len(char_list)-1)] = random.choice(string.printable)
        return "".join(char_list)
    
    elif strategy == 'edgecase':
        # Inject known bad integers or format strings
        return random.choice(["", "NULL", "A"*42, "\x00", "%s%s%s"])

# STEP 2: ACT (Fire the payload)
def fire_fuzz(payload_str):
    json_data = {"Payload": payload_str}
    try:
        response = requests.post(TARGET_URL, json=json_data, timeout=2)
        return response.status_code, response.text
    except requests.exceptions.RequestException:
        return 0, "Connection Refused"

# STEP 3: OODA LOOP (Main Logic)
def start_hunting():
    banner()
    print(f"[*] Starting Variant Hunting on {TARGET_URL}")
    print(f"[*] Seed Payload: {SEED_PAYLOAD}\n")

    crashes_found = 0

    for i in range(MAX_VARIANTS):
        # 1. Orient/Decide: Create a new variant
        variant = mutate_payload(SEED_PAYLOAD)
        
        # 2. Act: Send traffic
        status, response_text = fire_fuzz(variant)
        
        # 3. Observe: Analyze result
        # HTTP 500 means we successfully crashed the unhandled logic in C#
        if status == 500:
            print(f"[+] CRITICAL: Crash Detected! (Variant #{i})")
            print(f"    Payload Length: {len(variant)}")
            print(f"    Payload Content: {variant}")
            print(f"    Server Response: {response_text}\n")
            
            # Save the Proof of Concept (PoC)
            with open(f"crash_report_{i}.json", "w") as f:
                json.dump({"Payload": variant, "Error": response_text}, f)
            
            crashes_found += 1
            # We break after finding the specific bug, or you can keep going
            if "Buffer Edge Case Hit" in response_text:
                print("[!!!] TARGET DESTROYED: Specific Edge Case Identified.")
                break
        
        # Progress indicator
        if i % 100 == 0:
            print(f"[*] Progress: {i}/{MAX_VARIANTS} variants tested...")

    print(f"\n[*] Hunting Complete. Total Crashes Found: {crashes_found}")

if __name__ == "__main__":
    start_hunting()
