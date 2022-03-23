import csv
import base64
import os
import urllib.request
import shutil
from datetime import datetime
import schedule
import time


def update():

    try:
        print("Start!")
        os.mkdir(f"vpns/new")

        with open("vpns/lock", "w") as lock:
            lock.close()

        url = "http://www.vpngate.net/api/iphone/"
        response = urllib.request.urlopen(url)
        data = response.read()
        text = data.decode("utf-8")
        with open("vpns.csv", "w") as vpns:
            vpns.write(text)
            vpns.close()

        with open("vpns.csv", "r") as f:
            csv_file = csv.DictReader(
                f.readlines()[1:-1],
            )
            for row in csv_file:
                if (
                    row["CountryLong"] == "United States"
                    or row["CountryLong"] == "China"
                ):
                    continue
                if not os.path.exists(f"vpns/new/{row['CountryLong']}"):
                    os.mkdir(f"vpns/new/{row['CountryLong']}")
                vpn_file = open(f"vpns/new/{row['CountryLong']}/{row['IP']}.ovpn", "w")
                vpn_config = base64.b64decode(row["OpenVPN_ConfigData_Base64"]).decode(
                    "utf-8"
                )
                vpn_file.write(vpn_config)
                vpn_file.close()

        shutil.rmtree("vpns/old")
        os.rename("vpns/new", "vpns/old")
        os.remove("vpns/lock")
        print("Completed")

    except:
        with open("update_errors.txt", "a") as log:
            log.write(datetime.now().strftime("%d/%m/%y %H:%M:%S\n"))
            log.close()
        shutil.rmtree("vpns/new")
        os.remove("vpns/lock")
        print("Falied")


schedule.every().minute.do(update)

while True:
    schedule.run_pending()
    time.sleep(1)
