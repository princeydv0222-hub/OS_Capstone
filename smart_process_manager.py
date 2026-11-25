#!/usr/bin/env python3
"""
=============================================================================
Project Name : Smart Process Manager
Subject      : Operating Systems Capstone Project
Features     : Process Creation, Monitoring, Signals, Priority, Termination
Language     : Python 3 (Standard Library + Optional psutil)
=============================================================================
"""

import os
import sys
import time
import signal
import subprocess
import threading
from typing import Dict, Optional

# Optional psutil integration for enhanced CPU/Memory metrics
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class Colors:
    """ANSI color codes for clean terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class ManagedProcess:
    """
    Represents a Process Control Block (PCB) in the Operating System.
    Stores metadata, state, priority, and process handle.
    """
    def __init__(self, pid: int, name: str, command: str, popen_handle: Optional[subprocess.Popen] = None):
        self.pid = pid
        self.name = name
        self.command = command
        self.handle = popen_handle
        self.start_time = time.time()
        self.status = "RUNNING"  # RUNNING, PAUSED, TERMINATED, FINISHED
        self.simulated_priority = 0

    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed running time in seconds."""
        return round(time.time() - self.start_time, 1)

    def refresh_status(self) -> str:
        """Poll the process to detect if it has exited or changed state."""
        if self.handle:
            poll_result = self.handle.poll()
            if poll_result is not None:
                if self.status != "TERMINATED":
                    self.status = "FINISHED"
                return self.status

        # If not managed directly via handle, check if alive via signal 0
        try:
            os.kill(self.pid, 0)
        except OSError:
            if self.status != "TERMINATED":
                self.status = "FINISHED"

        return self.status

    def get_priority(self) -> int:
        """Get the current nice level (priority) of the process."""
        try:
            kernel_prio = os.getpriority(os.PRIO_PROCESS, self.pid)
            if self.simulated_priority != 0 and kernel_prio == 0:
                return self.simulated_priority
            return kernel_prio
        except (OSError, ProcessLookupError):
            return self.simulated_priority

    def get_resources(self) -> tuple[str, str]:
        """Return (CPU %, Memory RSS) if psutil is available, else fallback."""
        if HAS_PSUTIL:
            try:
                proc = psutil.Process(self.pid)
                cpu = f"{proc.cpu_percent(interval=0.0):.1f}%"
                mem = f"{proc.memory_info().rss / (1024 * 1024):.1f} MB"
                return cpu, mem
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return "--", "--"
        return "N/A", "N/A"


class SmartProcessManager:
    """
    Core OS Engine managing process creation, monitoring, signals, priority, and termination.
    """
    def __init__(self):
        # Process Table: Maps PID -> ManagedProcess
        self.processes: Dict[int, ManagedProcess] = {}

    # -------------------------------------------------------------------------
    # 1. PROCESS CREATION
    # -------------------------------------------------------------------------
    def create_process(self, command: str, name: Optional[str] = None) -> Optional[ManagedProcess]:
        """
        Creates and starts a new process asynchronously using subprocess.Popen.
        Corresponds to the fork() and exec() system calls in Unix.
        """
        if not name:
            name = command.split()[0] if command.strip() else "Unnamed"

        try:
            # Launch process in background without blocking manager
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )

            managed = ManagedProcess(pid=proc.pid, name=name, command=command, popen_handle=proc)
            self.processes[proc.pid] = managed
            print(f"{Colors.GREEN}[✓] Process created successfully! PID: {proc.pid} ({name}){Colors.RESET}")
            return managed
        except Exception as e:
            print(f"{Colors.FAIL}[✗] Failed to create process: {e}{Colors.RESET}")
            return None

    # -------------------------------------------------------------------------
    # 2. PROCESS MONITORING
    # -------------------------------------------------------------------------
    def list_processes(self):
        """
        Displays a structured Process Table (PCB summary) of all managed processes.
        """
        if not self.processes:
            print(f"{Colors.WARNING}No processes currently registered in the manager.{Colors.RESET}")
            return

        print(f"\n{Colors.BOLD}{Colors.CYAN}{'PID':<8} {'NAME':<16} {'STATUS':<12} {'NICE':<6} {'ELAPSED':<10} {'CPU %':<12} {'MEMORY':<14} {'COMMAND'}{Colors.RESET}")
        print("-" * 90)

        for pid, proc in list(self.processes.items()):
            status = proc.refresh_status()
            priority = proc.get_priority()
            cpu, mem = proc.get_resources()

            # Color status
            if status == "RUNNING":
                status_colored = f"{Colors.GREEN}{status:<12}{Colors.RESET}"
            elif status == "PAUSED":
                status_colored = f"{Colors.WARNING}{status:<12}{Colors.RESET}"
            else:
                status_colored = f"{Colors.FAIL}{status:<12}{Colors.RESET}"

            print(f"{proc.pid:<8} {proc.name[:15]:<16} {status_colored} {priority:<6} {f'{proc.elapsed_time}s':<10} {cpu:<12} {mem:<14} {proc.command[:25]}")
        print("-" * 90)

    # -------------------------------------------------------------------------
    # 3. SIGNALS (SIGSTOP, SIGCONT, SIGTERM, SIGKILL)
    # -------------------------------------------------------------------------
    def pause_process(self, pid: int) -> bool:
        """
        Sends SIGSTOP to pause the process execution without terminating it.
        Corresponds to moving the process from RUNNING state to WAITING/STOPPED state.
        """
        if pid not in self.processes:
            print(f"{Colors.FAIL}[✗] Process with PID {pid} is not tracked.{Colors.RESET}")
            return False

        proc = self.processes[pid]
        try:
            os.kill(pid, signal.SIGSTOP)
            proc.status = "PAUSED"
            print(f"{Colors.WARNING}[!] Sent SIGSTOP to PID {pid}. Process is now PAUSED.{Colors.RESET}")
            return True
        except ProcessLookupError:
            print(f"{Colors.FAIL}[✗] Process {pid} no longer exists.{Colors.RESET}")
            proc.status = "TERMINATED"
            return False
        except PermissionError:
            print(f"{Colors.FAIL}[✗] Permission denied to send signal to PID {pid}.{Colors.RESET}")
            return False

    def resume_process(self, pid: int) -> bool:
        """
        Sends SIGCONT to resume a paused process.
        Corresponds to moving the process from STOPPED state back to READY/RUNNING state.
        """
        if pid not in self.processes:
            print(f"{Colors.FAIL}[✗] Process with PID {pid} is not tracked.{Colors.RESET}")
            return False

        proc = self.processes[pid]
        try:
            os.kill(pid, signal.SIGCONT)
            proc.status = "RUNNING"
            print(f"{Colors.GREEN}[✓] Sent SIGCONT to PID {pid}. Process has RESUMED.{Colors.RESET}")
            return True
        except ProcessLookupError:
            print(f"{Colors.FAIL}[✗] Process {pid} no longer exists.{Colors.RESET}")
            proc.status = "TERMINATED"
            return False
        except PermissionError:
            print(f"{Colors.FAIL}[✗] Permission denied to send signal to PID {pid}.{Colors.RESET}")
            return False

    # -------------------------------------------------------------------------
    # 4. PRIORITY (NICE LEVEL ADJUSTMENT)
    # -------------------------------------------------------------------------
    def change_priority(self, pid: int, new_nice: int) -> bool:
        """
        Changes the CPU scheduling priority (nice value) of the process.
        Unix nice values range from -20 (highest priority) to 19 (lowest priority).
        Note: On Unix/macOS, lowering nice value (< 0) or certain sandbox profiles
        restrict setpriority system calls; if restricted, it is updated in the PCB.
        """
        if pid not in self.processes:
            print(f"{Colors.FAIL}[✗] Process with PID {pid} is not tracked.{Colors.RESET}")
            return False

        if not (-20 <= new_nice <= 19):
            print(f"{Colors.FAIL}[✗] Invalid nice value! Nice must be between -20 and 19.{Colors.RESET}")
            return False

        proc = self.processes[pid]
        try:
            old_nice = os.getpriority(os.PRIO_PROCESS, pid)
            os.setpriority(os.PRIO_PROCESS, pid, new_nice)
            proc.simulated_priority = new_nice
            print(f"{Colors.CYAN}[✓] Kernel priority updated for PID {pid}: nice {old_nice} -> {new_nice}{Colors.RESET}")
            return True
        except (PermissionError, OSError):
            old_nice = proc.get_priority()
            proc.simulated_priority = new_nice
            print(f"{Colors.CYAN}[✓] Priority updated in PCB for PID {pid}: nice {old_nice} -> {new_nice}")
            print(f"    (Note: Kernel-level setpriority was restricted by OS/sandbox policy){Colors.RESET}")
            return True
        except ProcessLookupError:
            print(f"{Colors.FAIL}[✗] Process {pid} no longer exists.{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.FAIL}[✗] Failed to adjust priority: {e}{Colors.RESET}")
            return False

    # -------------------------------------------------------------------------
    # 5. PROCESS TERMINATION
    # -------------------------------------------------------------------------
    def terminate_process(self, pid: int, force: bool = False) -> bool:
        """
        Terminates a process.
        - Graceful (default): sends SIGTERM, allowing clean resource release.
        - Force kill: sends SIGKILL, forcing immediate removal by the OS kernel.
        """
        if pid not in self.processes:
            print(f"{Colors.FAIL}[✗] Process with PID {pid} is not tracked.{Colors.RESET}")
            return False

        proc = self.processes[pid]
        sig_to_send = signal.SIGKILL if force else signal.SIGTERM
        sig_name = "SIGKILL (Force)" if force else "SIGTERM (Graceful)"

        try:
            os.kill(pid, sig_to_send)
            if proc.handle:
                try:
                    proc.handle.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    if not force:
                        print(f"{Colors.WARNING}[!] Process did not terminate within timeout. Escalating to SIGKILL...{Colors.RESET}")
                        os.kill(pid, signal.SIGKILL)
                        proc.handle.wait()

            proc.status = "TERMINATED"
            print(f"{Colors.GREEN}[✓] Process PID {pid} terminated via {sig_name}.{Colors.RESET}")
            return True
        except ProcessLookupError:
            proc.status = "TERMINATED"
            print(f"{Colors.WARNING}[!] Process {pid} was already dead.{Colors.RESET}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}[✗] Error terminating PID {pid}: {e}{Colors.RESET}")
            return False

    def terminate_all(self):
        """Cleanly terminates all active child processes to prevent orphan/zombie processes."""
        active = [p for p in self.processes.values() if p.refresh_status() in ("RUNNING", "PAUSED")]
        if not active:
            return

        print(f"\n{Colors.WARNING}[!] Cleaning up {len(active)} active process(es)...{Colors.RESET}")
        for proc in active:
            self.terminate_process(proc.pid, force=True)

    # -------------------------------------------------------------------------
    # 6. AUTOMATED CAPSTONE DEMO
    # -------------------------------------------------------------------------
    def run_automated_demo(self):
        """
        Runs an end-to-end automated demonstration of all core OS concepts:
        1. Process Creation (Workload processes)
        2. Process Monitoring & PCB inspection
        3. Priority adjustment (nice value)
        4. Signal Handling (SIGSTOP pause & SIGCONT resume)
        5. Process Termination (SIGTERM / SIGKILL)
        """
        print(f"\n{Colors.BOLD}{Colors.HEADER}=======================================================")
        print("          STARTING AUTOMATED OS CAPSTONE DEMO          ")
        print(f"======================================================={Colors.RESET}\n")
        time.sleep(1)

        # 1. Process Creation
        print(f"{Colors.BOLD}Step 1: Process Creation (Spawning 2 dummy worker processes){Colors.RESET}")
        p1 = self.create_process("python3 -c 'import time; [time.sleep(0.5) for _ in range(60)]'", name="Worker-Alpha")
        p2 = self.create_process("python3 -c 'import time; [time.sleep(0.5) for _ in range(60)]'", name="Worker-Beta")
        time.sleep(1)

        # 2. Process Monitoring
        print(f"\n{Colors.BOLD}Step 2: Monitoring Process Table (PCB Inspection){Colors.RESET}")
        self.list_processes()
        time.sleep(1.5)

        # 3. Priority Adjustment
        if p1:
            print(f"\n{Colors.BOLD}Step 3: Process Priority (Changing nice value of {p1.name}){Colors.RESET}")
            print("Increasing nice value to 10 (Lowering CPU scheduling priority):")
            self.change_priority(p1.pid, 10)
            self.list_processes()
            time.sleep(1.5)

        # 4. Signals: Pause & Resume
        if p2:
            print(f"\n{Colors.BOLD}Step 4: Signals - Pausing Process with SIGSTOP{Colors.RESET}")
            self.pause_process(p2.pid)
            self.list_processes()
            time.sleep(1.5)

            print(f"\n{Colors.BOLD}Step 5: Signals - Resuming Process with SIGCONT{Colors.RESET}")
            self.resume_process(p2.pid)
            self.list_processes()
            time.sleep(1.5)

        # 5. Process Termination
        print(f"\n{Colors.BOLD}Step 6: Process Termination (SIGTERM & SIGKILL){Colors.RESET}")
        if p1:
            self.terminate_process(p1.pid, force=False)
        if p2:
            self.terminate_process(p2.pid, force=True)

        self.list_processes()
        print(f"\n{Colors.BOLD}{Colors.GREEN}[✓] Automated Capstone Demo Completed Successfully!{Colors.RESET}\n")


# -----------------------------------------------------------------------------
# CLI INTERACTIVE MENU
# -----------------------------------------------------------------------------
def print_banner():
    print(f"""{Colors.CYAN}{Colors.BOLD}
  ╔═══════════════════════════════════════════════════════════╗
  ║            SMART PROCESS MANAGER (OS CAPSTONE)            ║
  ║  Creation • Monitoring • Signals • Priority • Termination ║
  ╚═══════════════════════════════════════════════════════════╝{Colors.RESET}""")


def main():
    manager = SmartProcessManager()

    # Graceful exit handler on Ctrl+C to clean up all processes
    def handle_exit(sig, frame):
        print(f"\n\n{Colors.WARNING}Interrupted! Cleaning up all child processes...{Colors.RESET}")
        manager.terminate_all()
        print(f"{Colors.GREEN}All processes cleared. Goodbye!{Colors.RESET}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)

    print_banner()
    if HAS_PSUTIL:
        print(f"{Colors.GREEN}[i] psutil detected: Real-time CPU % & Memory tracking enabled.{Colors.RESET}\n")
    else:
        print(f"{Colors.WARNING}[i] Running with Python Standard Library (psutil optional for detailed RAM/CPU %).{Colors.RESET}\n")

    while True:
        print(f"\n{Colors.BOLD}MAIN MENU:{Colors.RESET}")
        print("  [1] Launch New Custom Process")
        print("  [2] Launch Sample Background Worker (Sleep 60s)")
        print("  [3] Monitor & List All Processes")
        print("  [4] Pause Process (SIGSTOP)")
        print("  [5] Resume Process (SIGCONT)")
        print("  [6] Change Priority (Nice Value: -20 to 19)")
        print("  [7] Terminate Process (SIGTERM / SIGKILL)")
        print("  [8] Run Automated Capstone Demo")
        print("  [9] Exit")

        try:
            choice = input(f"{Colors.BOLD}Enter choice [1-9]: {Colors.RESET}").strip()
        except EOFError:
            break

        if choice == "1":
            cmd = input("Enter command to run (e.g. 'sleep 30' or 'python3 script.py'): ").strip()
            name = input("Enter a friendly name for this process: ").strip() or None
            if cmd:
                manager.create_process(cmd, name=name)
            else:
                print(f"{Colors.FAIL}Command cannot be empty.{Colors.RESET}")

        elif choice == "2":
            manager.create_process(
                "python3 -c 'import time; [time.sleep(1) for _ in range(60)]'",
                name="Sample-Worker"
            )

        elif choice == "3":
            manager.list_processes()

        elif choice == "4":
            try:
                pid = int(input("Enter PID to pause (SIGSTOP): ").strip())
                manager.pause_process(pid)
            except ValueError:
                print(f"{Colors.FAIL}Please enter a valid numeric PID.{Colors.RESET}")

        elif choice == "5":
            try:
                pid = int(input("Enter PID to resume (SIGCONT): ").strip())
                manager.resume_process(pid)
            except ValueError:
                print(f"{Colors.FAIL}Please enter a valid numeric PID.{Colors.RESET}")

        elif choice == "6":
            try:
                pid = int(input("Enter PID: ").strip())
                nice = int(input("Enter new nice value (-20 to 19): ").strip())
                manager.change_priority(pid, nice)
            except ValueError:
                print(f"{Colors.FAIL}Please enter valid numbers for PID and nice value.{Colors.RESET}")

        elif choice == "7":
            try:
                pid = int(input("Enter PID to terminate: ").strip())
                mode = input("Force kill with SIGKILL? (y/N): ").strip().lower()
                manager.terminate_process(pid, force=(mode == 'y'))
            except ValueError:
                print(f"{Colors.FAIL}Please enter a valid numeric PID.{Colors.RESET}")

        elif choice == "8":
            manager.run_automated_demo()

        elif choice == "9":
            manager.terminate_all()
            print(f"{Colors.GREEN}Exiting Smart Process Manager. Goodbye!{Colors.RESET}")
            break
        else:
            print(f"{Colors.FAIL}Invalid option. Please choose between 1 and 9.{Colors.RESET}")


if __name__ == "__main__":
    # If launched with --demo argument, run demo directly
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        manager = SmartProcessManager()
        manager.run_automated_demo()
    else:
        main()
