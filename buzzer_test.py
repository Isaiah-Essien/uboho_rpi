'''Just testing this buzzer to make sure it works'''

import time
from gpiozero import Buzzer

# Initialize buzzer on GPIO pin 17
buzzer = Buzzer(17)

print("[INFO] Buzzer test started. It will buzz on and off for 5 cycles.")

for i in range(5):
    print(f"[BUZZ] Cycle {i+1}: ON")
    buzzer.on()
    time.sleep(1)  # 1 second ON
    buzzer.off()
    print(f"[BUZZ] Cycle {i+1}: OFF")
    time.sleep(1)  # 1 second OFF

print("[INFO] Buzzer test completed.")
