from flask import Flask, render_template, request, redirect, flash
import subprocess
import os
import time
from threading import Thread

app = Flask(__name__)
app.secret_key = 'some_secret'
app.debug = True


@app.route('/')
def index():
    wifi_ap_array = scan_wifi_networks()

    return render_template('app.html', wifi_ap_array = wifi_ap_array)


@app.route('/manual_ssid_entry')
def manual_ssid_entry():
    return render_template('manual_ssid_entry.html')


@app.route('/save_credentials', methods = ['GET', 'POST'])
def save_credentials():
    ssid = request.form['ssid']
    wifi_key = request.form['wifi_key']

    create_wpa_supplicant(ssid, wifi_key)

    if wpa_auth_check() == True:
        def sleep_and_start_ap():
            time.sleep(5)
            set_ap_client_mode()
        t = Thread(target=sleep_and_start_ap)
        t.start()

        return render_template('save_credentials.html', ssid = ssid)
    else:
        flash("Incorrect wireless key")
        return redirect('/')



######## FUNCTIONS ##########

def scan_wifi_networks():
    iwlist_raw = subprocess.Popen(['iwlist', 'scan'], stdout=subprocess.PIPE)
    ap_list, err = iwlist_raw.communicate()
    ap_array = []

    for line in ap_list.decode('utf-8').rsplit('\n'):
        if 'ESSID' in line:
            ap_ssid = line[27:-1]
            if ap_ssid != '':
                ap_array.append(ap_ssid)

    # Remove duplicate entries
    ap_array = list(set(ap_array))

    return ap_array

def create_wpa_supplicant(ssid, wifi_key):
    temp_conf_file = open('wpa_supplicant.conf.tmp', 'w')

    temp_conf_file.write('ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n')
    temp_conf_file.write('update_config=1\n')
    temp_conf_file.write('\n')
    temp_conf_file.write('network={\n')
    temp_conf_file.write('	ssid="' + ssid + '"\n')

    if wifi_key == '':
        temp_conf_file.write('	key_mgmt=NONE\n')
    else:
        temp_conf_file.write('	psk="' + wifi_key + '"\n')

    temp_conf_file.write('	}')

    temp_conf_file.close

    os.system('mv wpa_supplicant.conf.tmp /etc/wpa_supplicant/wpa_supplicant.conf')

def set_ap_client_mode():
    os.system('rm -f /etc/raspiwifi/host_mode')
    os.system('rm /etc/cron.raspiwifi/aphost_bootstrapper')
    os.system('cp /usr/lib/raspiwifi/reset_device/static_files/apclient_bootstrapper /etc/cron.raspiwifi/')
    os.system('chmod +x /etc/cron.raspiwifi/apclient_bootstrapper')
    os.system('mv /etc/dnsmasq.conf.original /etc/dnsmasq.conf')
    os.system('mv /etc/dhcpcd.conf.original /etc/dhcpcd.conf')
    os.system('cp /usr/lib/raspiwifi/reset_device/static_files/isc-dhcp-server.apclient /etc/default/isc-dhcp-server')
    os.system('reboot')

def config_file_hash():
    config_file = open('/etc/raspiwifi/raspiwifi.conf')
    config_hash = {}

    for line in config_file:
        line_key = line.split("=")[0]
        line_value = line.split("=")[1].rstrip()
        config_hash[line_key] = line_value

    return config_hash

def wpa_auth_check():
    os.system('wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf')

    time.sleep(4)

    wpa_cli_raw = subprocess.Popen(['wpa_cli', '-i', 'wlan0', 'status'], stdout=subprocess.PIPE)
    wpa_cli_out, err = wpa_cli_raw.communicate()

    if 'wpa_state=COMPLETED' in wpa_cli_out.decode('utf-8'):
        os.system('pkill wpa_supplicant')
        return True
    else:
        os.system('pkill wpa_supplicant')
        return False

def reboot_device():
    time.sleep(1)
    os.system('reboot')

if __name__ == '__main__':
    config_hash = config_file_hash()

    if config_hash['ssl_enabled'] == "1":
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']), ssl_context='adhoc')
    else:
        app.run(host = '0.0.0.0', port = int(config_hash['server_port']))
