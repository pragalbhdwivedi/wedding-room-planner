"""Leased jobs; applying a proposal always requires the owner."""
import signal
import time
from .jobs import process_one

running = True


def stop(*_):
    global running
    running = False


def main():
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    while running:
        try:process_one()
        except Exception:pass  # Transient database failures retry; health becomes stale.
        for _ in range(2):
            if not running:break
            time.sleep(1)


if __name__=="__main__":main()
