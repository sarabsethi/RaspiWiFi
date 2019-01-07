import RPi.GPIO as GPIO
import os
import time
import subprocess
import reset_lib

GPIO.setmode(GPIO.BCM)
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_UP)

counter = 0
serial_last_four = subprocess.check_output(['cat', '/proc/cpuinfo'])[-5:-1].decode('utf-8')
config_hash = reset_lib.config_file_hash()
ssid_prefix = config_hash['ssid_prefix'] + " "
hostapd_reset_required = reset_lib.hostapd_reset_check(ssid_prefix)


if hostapd_reset_required == True:
    reset_lib.update_hostapd(ssid_prefix, serial_last_four)
    os.system('reboot')

# This is the main logic loop waiting for a button to be pressed on GPIO 20 for 10 seconds.
# If that happens the device will reset to its AP Host mode allowing for reconfiguration on a new network.
while True:
    while GPIO.input(20) == 0:
        time.sleep(1)
        counter = counter + 1

        print(counter)

        if counter == 9:
            reset_lib.reset_to_host_mode()

        if GPIO.input(20) == 1:
            counter = 0
            break

    time.sleep(1)
