# run_presence_os.py

print("=== STARTUP DEBUG ===")
try:
    import fastapi
    import uvicorn
    print("SUCCESS: FastAPI and Uvicorn are importable!")
    print(f"FastAPI version: {fastapi.__version__}")
    print(f"Uvicorn version: {uvicorn.__version__}")
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
print("=== END STARTUP DEBUG ===")


import asyncio
import sys
import os

import os
import logging # Assuming your kernel logger isn't set up yet
logging.basicConfig(level=logging.INFO)
logging.info("--- Initial Script Environment Variables ---")
for k, v in sorted(os.environ.items()):
    if "CUDA" in k or "NVIDIA" in k: # Focus on relevant ones
        logging.info(f"{k}={v}")
logging.info("-----------------------------------------")
# ... rest of your script


# In run_presence_os.py
import logging # Or use your kernel's logger setup if it's early
import torch

logging.info("--- Early PyTorch CUDA Check ---")
logging.info(f"PyTorch version: {torch.__version__}")
is_available = False
try:
    is_available = torch.cuda.is_available()
    logging.info(f"torch.cuda.is_available() check: {is_available}")
    if is_available:
        logging.info(f"CUDA version PyTorch compiled with: {torch.version.cuda}")
        logging.info(f"Device count: {torch.cuda.device_count()}")
        if torch.cuda.device_count() > 0:
            logging.info(f"Device name: {torch.cuda.get_device_name(0)}")
            # Try a tiny CUDA operation
            # x = torch.tensor([1.0, 2.0]).cuda() # This will def initialize context
            # logging.info(f"Tiny tensor on CUDA: {x}")
            # del x
            # torch.cuda.empty_cache()
    else:
        logging.warning("Early check: CUDA not available to PyTorch.")
except Exception as e_cuda_check:
    logging.error(f"Early PyTorch CUDA check FAILED: {e_cuda_check}", exc_info=True)
logging.info("----------------------------------")

# ... then proceed with your Kernel initialization and module loading ...


import time
import argparse # For command-line arguments for config/modules dirs
import traceback # For printing tracebacks on unexpected errors
from pathlib import Path
from typing import Optional # For type hinting

# --- Path Setup ---
_launcher_dir = str(Path(__file__).resolve().parent)
if _launcher_dir not in sys.path:
    sys.path.insert(0, _launcher_dir)

# --- Import Kernel Components ---
try:
    # Need PresenceKernel to run, and SystemState for checking state in launcher logic
    from PresenceOS_kernel import PresenceKernel, SystemState
    KERNEL_IMPORTED_SUCCESSFULLY = True
except ImportError as e:
    print(f"FATAL ERROR (Launcher): Could not import PresenceKernel/SystemState from PresenceOS_kernel.py: {e}")
    print(f"Ensure PresenceOS_kernel.py is in the directory: {_launcher_dir}")
    KERNEL_IMPORTED_SUCCESSFULLY = False
except Exception as e_general:
    print(f"FATAL ERROR (Launcher): An unexpected error occurred during import of PresenceOS_kernel: {e_general}")
    traceback.print_exc()
    KERNEL_IMPORTED_SUCCESSFULLY = False

# --- Main Asynchronous Logic ---
async def start_kernel_main_logic(config_path: str, modules_path: str):
    """
    Initializes, boots, and runs the PresenceOS kernel until shutdown.
    """
    print("\n" + "="*70);
    print("   PresenceOS - Modular Application Platform Kernel (Async Launcher)")
    print("="*70 + "\n")

    kernel: Optional[PresenceKernel] = None # Define kernel here for access in finally block
    try:
        # Instantiate the kernel
        kernel = PresenceKernel(config_dir=config_path, modules_dir=modules_path)

        # Boot the kernel (initializes components, loads modules, starts CLI thread)
        if await kernel.boot():
            # --- Kernel Booted Successfully ---
            print(f"\n✓ PresenceOS async kernel booted successfully (via launcher).");
            print(f"  Config Dir:  {kernel.config_dir.resolve()}");
            print(f"  Modules Dir: {kernel.modules_dir_path.resolve()}");
            
            cli_status_msg = 'Inactive / Not loaded' # Default status
            if kernel.cli:
                if kernel._cli_thread and kernel._cli_thread.is_alive():
                    cli_status_msg = 'Active (in dedicated thread)'
                else:
                    # This state implies CLI object exists but its thread isn't running (e.g., start failed internally)
                    cli_status_msg = 'Initialized but CLI thread not active/found' 
            print(f"  CLI Status:  {cli_status_msg}")
            
            # Brief pause allows background tasks like CLI thread to fully start
            await asyncio.sleep(0.1) 
            
            print("\nKernel running asynchronously... Press Ctrl+C or use 'shutdown' command in CLI.")
            
            # --- Wait for Kernel to Stop ---
            # Await the kernel's main internal loop task. This task will only complete
            # when the kernel is shutting down (i.e., when kernel._running is cleared).
            # This is the primary mechanism keeping the launcher's async context alive.
            if kernel._main_loop_task:
                try:
                    await kernel._main_loop_task 
                    # If we get here, _main_loop_task finished cleanly (likely due to kernel._running being cleared)
                    print("Launcher: Kernel's main_loop_task has completed.")
                except asyncio.CancelledError:
                    # This happens if start_kernel_main_logic itself is cancelled while awaiting the main_loop_task
                    print("Launcher: Awaiting kernel's main_loop_task was cancelled.")
                    # Ensure kernel shutdown is triggered if it wasn't the source of cancellation
                    if kernel and kernel.state != SystemState.SHUTTING_DOWN: # type: ignore
                        print("Launcher (CancelledError): Kernel state wasn't SHUTTING_DOWN, ensuring shutdown.")
                        await kernel.shutdown()

            else: # Should not happen if boot succeeded
                print("Launcher: CRITICAL - Kernel's main_loop_task not found after successful boot! Forcing shutdown.")
                if kernel._running.is_set(): kernel._running.clear()
                await kernel.shutdown() # Attempt shutdown anyway

            print("\nLauncher: Kernel has stopped or shutdown sequence initiated.")
            # --- End Waiting Logic ---

        else: # kernel.boot() returned False
            print("\n✗ PresenceOS async kernel boot sequence failed. Check logs for details.");
            # Allow finally block to handle cleanup if kernel object exists

    except asyncio.CancelledError:
        # Catch cancellation of start_kernel_main_logic itself (e.g., from KeyboardInterrupt in asyncio.run)
        print("\nLauncher: Main async task (start_kernel_main_logic) received CancelledError.")
        if kernel and kernel.state != SystemState.SHUTTING_DOWN: # type: ignore
            print("Launcher (CancelledError): Ensuring kernel shutdown sequence is triggered...")
            await kernel.shutdown() # Attempt graceful shutdown

    except Exception as e:
        # Catch any other unexpected error during kernel setup or run
        print(f"\nCRITICAL UNHANDLED ERROR in launcher's async logic (start_kernel_main_logic): {e}");
        logging.getLogger("PresenceOSLauncher").critical(f"Unhandled exception: {e}", exc_info=True);
        if kernel and kernel.state != SystemState.SHUTTING_DOWN: # type: ignore
             print("Launcher (Exception): Attempting emergency shutdown of kernel...")
             await kernel.shutdown() # Best effort shutdown
    finally:
        # This block runs regardless of whether the try block succeeded, failed, or was cancelled.
        print("\nLauncher: Async logic (start_kernel_main_logic) entering 'finally' block.")
        if kernel:
            # Give kernel's shutdown mechanisms (potentially running concurrently) time to finish.
            if kernel.state == SystemState.SHUTTING_DOWN: # type: ignore
                print("Launcher's finally: Kernel is in SHUTTING_DOWN state. Waiting briefly...")
                shutdown_wait_start = time.monotonic()
                # Wait up to 15s for kernel state to change from SHUTTING_DOWN
                while kernel.state == SystemState.SHUTTING_DOWN and (time.monotonic() - shutdown_wait_start < 15.0): # type: ignore
                    await asyncio.sleep(0.2) 
            print(f"Launcher's finally: Final observed kernel state: {kernel.state.name if kernel.state else 'Unknown'}") # type: ignore
        else:
            print("Launcher's finally: Kernel object was not successfully created or is None.")
        print("Launcher: Async logic (start_kernel_main_logic) finished.")


# --- Synchronous Main Entry Point ---
if __name__ == "__main__":
    # Configure basic logging (kernel reconfigures based on its settings later)
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s', 
                        datefmt='%Y-%m-%d %H:%M:%S', # Use valid date format
                        stream=sys.stdout)

    # Exit immediately if critical kernel components couldn't be imported
    if not KERNEL_IMPORTED_SUCCESSFULLY:
        print("Launcher: Cannot proceed because PresenceKernel could not be imported. Exiting.")
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PresenceOS Async Kernel Launcher");
    parser.add_argument("-c", "--config", default="config", help="Path to the configuration directory (default: 'config')");
    parser.add_argument("-m", "--modules", default="modules", help="Path to the modules directory (default: 'modules')");
    args = parser.parse_args()

    main_loop = None
    try:
        # asyncio.run() is generally preferred for simplicity if detailed loop control isn't needed
        asyncio.run(start_kernel_main_logic(args.config, args.modules))
        
        # --- Manual Loop Example (Alternative to asyncio.run) ---
        # main_loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(main_loop)
        # main_task = main_loop.create_task(start_kernel_main_logic(args.config, args.modules))
        # main_loop.run_until_complete(main_task)
        # --- End Manual Loop Example ---

    except KeyboardInterrupt:
        print("\nLauncher: KeyboardInterrupt caught in synchronous wrapper. Exiting.")
        # asyncio.run() should handle cleanup of the loop and tasks on Ctrl+C gracefully.
        # If using manual loop, need more explicit cancellation here.
        # if main_loop and main_task and not main_task.done():
        #     main_task.cancel()
        #     try:
        #         main_loop.run_until_complete(main_task) # Allow cancellation
        #     except asyncio.CancelledError:
        #         pass # Expected
    except Exception as e_outer:
        print(f"Launcher: Unexpected error in synchronous wrapper: {e_outer}")
        traceback.print_exc()
    finally:
        print("PresenceOS Launcher synchronous wrapper finished.")
        # --- Manual Loop Cleanup (if using manual loop alternative) ---
        # if main_loop and not main_loop.is_closed():
        #     print("Launcher: Closing event loop.")
        #     # Optional: Gather and cancel remaining tasks before closing loop
        #     # remaining_tasks = asyncio.all_tasks(main_loop) ... etc ...
        #     main_loop.close()
        #     print("Launcher: Event loop closed.")
        # --- End Manual Loop Cleanup ---
        
        logging.shutdown() # Ensure all logging handlers are closed
        print("Launcher: Exiting.")