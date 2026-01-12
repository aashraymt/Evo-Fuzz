# Building an Evolutionary Fuzzer

The sole purpose of this project was to learn fuzzing by building one from scratch. I wanted to move beyond just running tools and actually understand the mechanics of mutation strategies and code coverage. I built a custom evolutionary engine in Python that applies genetic algorithms to "breed" malicious inputs, relying on response feedback (heuristics) to discover edge cases. This repo documents my experiments in breaking both a .NET Web API (logic bombs) and a Linux binary (buffer overflows) using nothing but my own code.

### The Experiment
I created a lab environment 
1.  A C# .NET Core Web API that I intentionally engineered with a "Logic Bomb" (a hidden crash that only triggers if the input length is exactly 42 characters).
2.  A Python script that doesn't just guess randomly—it uses **Genetic Algorithms**. It takes "parents" (inputs), mixes them (crossover), mutates them, and learns from the server's response.

<img width="1318" height="741" alt="image" src="https://github.com/user-attachments/assets/40da68ba-ed99-4edf-a6f0-0fce4d16a8d6" />

*The moment the fuzzer figured out the logic bomb. Left: Python finding the crash. Right: The C# server exploding.*

---

### Why Evolutionary?
Standard fuzzers are "dumb"—they just throw random trash at the server. 
I wanted to implement an **OODA Loop** (Observe, Orient, Decide, Act).

* **Observe:** The fuzzer checks the API response. Did the response length change? That means we hit a new code path!
* **Orient:** If we found a new path, add that input to the "Gene Pool."
* **Decide:** Pick two successful parents and breed them (or mutate them).
* **Act:** Fire the new child payload.

I also implemented a **"Dictionary Mutation"** strategy. Pure evolution takes a long time, so I taught the fuzzer to occasionally "cheat" by injecting known bad strings (like `NULL` bytes or long buffer overflows). This turned out to be the key to finding the bug quickly.

---

### The Crash
The fuzzer successfully identified the logic bomb (`data.Payload.Length == 42`) in Generation 0 by using a dictionary replacement strategy.

Here is the actual Proof of Concept (PoC) it generated automatically:

<img width="902" height="93" alt="image" src="https://github.com/user-attachments/assets/dc1cefd5-e95b-4815-9290-f6103ab8a955" />


It flagged the crash as "Unique" by hashing the stack trace, so I didn't get spammed with 1,000 logs for the same bug.

---

### How I Built It
**The Target (C# .NET 8.0)**
I simulated a "Critical Memory Failure" using an unhandled exception.
```csharp

The Logic Bomb in Program.cs
//if (data.Payload.Length == 42)
{
    throw new InvalidOperationException("CRITICAL MEMORY FAILURE: Buffer Edge Case Hit!");
}

```
## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/aashraymt/Evo-Fuzz.git
cd Evo-Fuzz

cd VulnerableAPI

# Force generate the project files (if missing)
dotnet new web --force

# Start the server on port 5000
dotnet run --urls "http://localhost:5000"
cd ../Fuzzer

# Run the evolutionary engine
python3 fuzzer.py
```
I built this project purely for educational purposes and research. Only run this on your own local labs.
