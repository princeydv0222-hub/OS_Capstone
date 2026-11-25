# Smart Process Manager (OS Capstone Project)

A lightweight, simple, and complete **Operating System Process Manager** built in Python. This project demonstrates core OS process lifecycle management concepts including process creation, real-time monitoring, Unix signals, CPU scheduling priority (nice levels), and graceful/forced process termination.

---

## 📌 Project Objectives & OS Concepts Covered

| OS Concept | Implementation in this Project | Operating System Mechanism |
| :--- | :--- | :--- |
| **Process Creation** | `create_process(cmd, name)` | Corresponds to `fork()` + `exec()` system calls using `subprocess.Popen`. |
| **Process Control Block (PCB)** | `ManagedProcess` class | Stores PID, process name, command line, start timestamp, status, and state. |
| **Process Monitoring** | `list_processes()` | Inspects status (`RUNNING`, `PAUSED`, `FINISHED`, `TERMINATED`), elapsed time, nice level, and resource stats. |
| **Signals & State Transitions** | `pause_process()`, `resume_process()` | Sends `SIGSTOP` (transitions to `PAUSED`/`STOPPED`) and `SIGCONT` (transitions back to `READY`/`RUNNING`). |
| **CPU Scheduling & Priority** | `change_priority(pid, nice)` | Reads and modifies Unix nice levels (-20 to 19) via `os.getpriority()` and `os.setpriority()`. |
| **Process Termination** | `terminate_process(pid, force)` | Sends `SIGTERM` (graceful exit) or `SIGKILL` (immediate kernel kill), avoiding zombie/orphan processes. |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+ (Mac, Linux, or WSL on Windows)
- Uses **Python Standard Library** by default (zero external dependencies required!).
- *(Optional)* `pip install psutil` to display real-time CPU % and Memory RSS in the process monitor table.

---

## 🖥️ Running the Project

### 1. Interactive Menu Mode
Run the main script to enter the interactive CLI:
```bash
python3 smart_process_manager.py
```

You will be greeted with an intuitive menu:
```text
  ╔═══════════════════════════════════════════════════════════╗
  ║            SMART PROCESS MANAGER (OS CAPSTONE)            ║
  ║  Creation • Monitoring • Signals • Priority • Termination ║
  ╚═══════════════════════════════════════════════════════════╝

MAIN MENU:
  [1] Launch New Custom Process
  [2] Launch Sample Background Worker (Sleep 60s)
  [3] Monitor & List All Processes
  [4] Pause Process (SIGSTOP)
  [5] Resume Process (SIGCONT)
  [6] Change Priority (Nice Value: -20 to 19)
  [7] Terminate Process (SIGTERM / SIGKILL)
  [8] Run Automated Capstone Demo
  [9] Exit
```

### 2. Automated Capstone Demo Mode
You can also run the self-contained automated demo with a single command (great for lab presentations and quick evaluations):
```bash
python3 smart_process_manager.py --demo
```
This runs an end-to-end 15-second walkthrough:
1. Spawns two dummy worker processes (`Worker-Alpha` and `Worker-Beta`).
2. Displays the initial Process Table (PCB).
3. Adjusts CPU priority (nice level) of `Worker-Alpha`.
4. Sends `SIGSTOP` to pause `Worker-Beta` and checks state.
5. Sends `SIGCONT` to resume `Worker-Beta`.
6. Gracefully terminates `Worker-Alpha` with `SIGTERM` and force-kills `Worker-Beta` with `SIGKILL`.

---

## 📁 File Structure

```
OS Capstone/
│
├── smart_process_manager.py   # Complete implementation (PCB, Manager, Signals, Priority, CLI)
└── README.md                  # Project overview, OS theory & documentation
```

---

## 🧠 Technical Details for OS Viva / Presentation

1. **Why does Nice value range from -20 to 19?**
   - In Unix/Linux, lower nice values mean "less nice" to other processes, granting the process **higher** priority and more CPU time slices.
   - Standard user processes can only increase their nice value (reduce priority). Lowering it below 0 requires root/sudo privileges.

2. **Difference between `SIGTERM` and `SIGKILL`:**
   - `SIGTERM` (signal 15) is a polite termination request that the process can catch or handle to flush buffers and release files.
   - `SIGKILL` (signal 9) cannot be caught or ignored; the OS kernel forcibly unmaps the process address space immediately.

3. **Orphan & Zombie Prevention:**
   - When the manager exits or receives `Ctrl+C` (SIGINT), it triggers `terminate_all()` to clean up all spawned child processes, preventing abandoned orphan processes.
