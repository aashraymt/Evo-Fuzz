import requests
import random
import string
import time
import json
import hashlib

# ==========================================
# CONFIGURATION & GENETIC PARAMETERS
# ==========================================
TARGET_URL = "http://localhost:5000/api/process-data"
INITIAL_SEED = "A" * 10
MAX_GENERATIONS = 50       # How many "evolutionary cycles" to run
POPULATION_SIZE = 20       # Max 'fittest' inputs to keep
MUTATION_RATE = 0.6        # 60% chance to mutate, 40% chance to crossover

# DICTIONARY: "Magic Values" that often break parsers (Video Concept 2)
BAD_CHARS = [
    "%00", "\x00", "\n", "\r", "../", "..\\", 
    "A"*42,                # The specific logic bomb for this lab
    "%s%s%s",              # Format strings
    "99999999999",         # Integer overflow
    "null", "None", "TRUE" # Json types
]

# STATE TRACKING
population = [INITIAL_SEED]  # Our "Gene Pool"
seen_crashes = set()         # For Deduplication (Video Concept 3)
seen_paths = set()           # To track unique response lengths (Fitness Proxy)

def banner():
    print("""
    =============================================
      EVO-FUZZ: Evolutionary Variant Hunter
      Features: Genetic Algo, Dedup, Dictionary
    =============================================
    """)

# ==========================================
# GENETIC OPERATORS (Video Concept 1 & 2)
# ==========================================

def get_fitness_proxy(response_text):
    """
    Since we don't have code coverage (black box), we use 
    Response Length as a proxy for 'Interestingness'.
    """
    return len(response_text)

def crossover(parent1, parent2):
    """
    Splicing: Takes the first half of Parent A and second half of Parent B.
    """
    split1 = len(parent1) // 2
    split2 = len(parent2) // 2
    return parent1[:split1] + parent2[split2:]

def mutate(payload):
    """
    Applies Dictionary Injection, Bit-flipping, or Expansion.
    """
    strategy = random.choice(['bitflip', 'insert_dict', 'expand', 'shrink'])
    
    if strategy == 'insert_dict':
        # Inject a nasty known-bad string
        token = random.choice(BAD_CHARS)
        pos = random.randint(0, len(payload))
        return payload[:pos] + token + payload[pos:]
        
    elif strategy == 'bitflip':
        if not payload: return payload
        char_list = list(payload)
        pos = random.randint(0, len(char_list)-1)
        char_list[pos] = random.choice(string.printable)
        return "".join(char_list)
        
    elif strategy == 'expand':
        return payload + random.choice(string.ascii_letters) * random.randint(1, 10)
    
    elif strategy == 'shrink':
        if len(payload) < 2: return payload
        return payload[:-1]
    
    return payload

# ==========================================
# EXECUTION ENGINE
# ==========================================

def fire_fuzz(payload_str):
    json_data = {"Payload": payload_str}
    try:
        # We catch timeouts as interesting events too
        response = requests.post(TARGET_URL, json=json_data, timeout=2)
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return 0, str(e)

def save_crash(payload, error_msg, crash_id):
    filename = f"crash_{crash_id}.json"
    with open(filename, "w") as f:
        json.dump({"Payload": payload, "Error": error_msg}, f)
    print(f"    [Disk] PoC saved to {filename}")

# ==========================================
# MAIN EVOLUTIONARY LOOP (The OODA Loop)
# ==========================================
def start_hunting():
    banner()
    print(f"[*] Seeding population with: {INITIAL_SEED}")
    
    global population
    total_crashes = 0
    
    for generation in range(MAX_GENERATIONS):
        print(f"\n--- Generation {generation} (Pop Size: {len(population)}) ---")
        
        # Create next generation
        next_gen = []
        
        # We try to create roughly 50 new children per generation
        for _ in range(50):
            # 1. SELECTION: Pick parents
            parent1 = random.choice(population)
            parent2 = random.choice(population)
            
            # 2. REPRODUCTION: Crossover or Mutate?
            if random.random() > MUTATION_RATE:
                child = crossover(parent1, parent2)
            else:
                child = mutate(parent1)
            
            # 3. ACT: Fire Payload
            status, resp_text = fire_fuzz(child)
            
            # 4. OBSERVE & ORIENT (Triage)
            if status == 500:
                # CRASH DEDUPLICATION (Video Concept 3)
                # Hash the error message to see if it's unique
                crash_sig = hashlib.md5(resp_text.encode()).hexdigest()
                
                if crash_sig not in seen_crashes:
                    print(f"[+] CRITICAL: New Unique Crash! (Sig: {crash_sig[:8]})")
                    print(f"    Payload: {child[:50]}...") # Truncate for readability
                    save_crash(child, resp_text, crash_sig[:8])
                    seen_crashes.add(crash_sig)
                    total_crashes += 1
                else:
                    # We saw this crash already, ignore it (Noise reduction)
                    pass

            elif status == 200:
                # SURVIVAL OF THE FITTEST (Fitness Function)
                # If this payload produced a response length we haven't seen before,
                # it implies we hit a new code path. Keep it!
                path_sig = len(resp_text)
                if path_sig not in seen_paths:
                    print(f"[*] Evolution: Found new response path (Len: {path_sig})")
                    seen_paths.add(path_sig)
                    next_gen.append(child) # It survives to breed
        
        # CULLING / ELITISM
        # Add new survivors to population, but cap the size to prevent bloat
        population.extend(next_gen)
        # Keep only unique inputs to maintain genetic diversity
        population = list(set(population)) 
        
        if len(population) > POPULATION_SIZE:
            # Randomly cull, but biased towards keeping shorter (cleaner) inputs
            population = sorted(population, key=len)[:POPULATION_SIZE]

    print(f"\n[*] Hunting Complete. Unique Crashes Found: {total_crashes}")

if __name__ == "__main__":
    start_hunting()
