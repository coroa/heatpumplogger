import os
import time
import traceback
from csv import DictWriter

import pandas as pd
from bs4 import BeautifulSoup
from websockets.sync.client import ClientConnection, connect
from collections import OrderedDict
# %% config
log_interval = 60

non_numeric_var = frozenset(["Anlagenstatus/Betriebszustand"])
variable_mapping = {
    "Temperaturen/Warmwasser-Ist": ("Tw Warmasser-Ist", "°C"),
    "Temperaturen/Warmwasser-Soll": ("Tw Warmwasser-Soll", "°C"),
    "Temperaturen/Außentemperatur": ("Ta Außentemperatur", "°C"),
    "Temperaturen/Vorlauf": ("Th Vorlauf-Ist", "°C"),
    "Temperaturen/Rücklauf": ("Th Rücklauf-Ist", "°C"),
    "Temperaturen/Rückl.-Soll": ("Th Rücklauf-Soll", "°C"),
    "Temperaturen/Mischkreis1-Vorlauf": ("Th Mischkreis1-Vorlau-Ist", "°C"),
    "Temperaturen/Mischkreis1 VL-Soll": ("Th Mischkreis1-VL-Soll", "°C"),
    "Temperaturen/VD-Heizung": ("Th VD-Heizung", "°C"),
    "Temperaturen/Ansaug VD": ("Temperaturen/Ansaug VD", "°C"),
    "Wärmequelle-Ein": ("Wärmequelle-Ein", "°C"),
    "Anlagenstatus/Betriebszustand": ("Betriebszustand", ""),
    "Anlagenstatus/Heizleistung Ist": ("Heizleistung Ist", "kW"),
    "Anlagenstatus/Abtaubedarf": ("Abtaubedarf", "%"),
    "Wärmemenge/Heizung": ("Wärmemenge_Heizung", "kWh"),
    "Wärmemenge/Warmwasser": ("Wärmemenge_Warmwasser", "kWh"),
    # "Wärmemenge/Gesamt" :  ("kWh"),
    "Eingesetzte Energie/Heizung": ("Eingesetzte Energie_Heizung", "kWh"),
    "Eingesetzte Energie/Warmwasser": ("Eingesetzte Energie_Warmwasser", "kWh"),
    # "Eingesetzte Energie/Gesamt" =:  ("kWh"),
    "Eingänge/Durchfluss": ("Durchfluss", "l/h"),
}

status_mapping = {
    "Anlagenstatus/Betriebszustand" : {'' : 0, 'Heizen': 1, 'WW': 1, 'ABT':2},
    "Eingänge/STB E-Stab" : {'Aus' : 0, 'Ein' : 1},
    "Ausgänge/HUP": {'Aus' : 0, 'Ein' : 1},
    "Ausgänge/BUP": {'Aus' : 0, 'Ein' : 1},
    "Ausgänge/Verdichter": {'Aus' : 0, 'Ein' : 1},
    "Ausgänge/VD-Heizung": {'Aus' : 0, 'Ein' : 1}
    }
    
status_vars = list(status_mapping.keys())

# %%
def call(ws: ClientConnection, cmd) -> BeautifulSoup:
    ws.send(cmd)
    return BeautifulSoup(ws.recv(timeout=10), "html.parser")


def select(ws: ClientConnection, id: str) -> dict[str, tuple]:
    id_map = {}
    info_items = call(ws, f"GET;{id}")
    section_items = info_items.find(name="content").find_all("item", recursive=True)
    for section_it in section_items[:-1]:
        # print(section_it)
        section = section_it.find("name").text
        id_map.update(
            {
                it["id"]: (section, it.find("name").text)
                for it in section_it.find_all("item")
            }
        )

    return id_map


def update(ws: ClientConnection, id_map) -> list[tuple]:
    data = []
    for it in call(ws, "REFRESH").find_all("item"):
        if it["id"] not in id_map:
            # skip sections
            continue
        section, param = id_map[it["id"]]
        value_it = it.find("value", recursive=False)
        if value_it:
            value = value_it.text
            data.append((section, param, value))
    return data


def update_existing_file(fieldnames: list[str]) -> str:
    date_str = pd.Timestamp.now().strftime("%y-%m-%d")
    filename = f"data/log_{date_str}.csv"
    if not os.path.exists(filename):
        return "startup"

    tt = time.time()
    print("Loading from disk and extending with new columns..", end="")
    df = pd.read_csv(filename, index_col=0)

    # update file if new columns or new order
    changed_columns = fieldnames[1:] != list(df.columns)
    if changed_columns:
        df.reindex(columns=fieldnames[1:]).to_csv(filename)
    print(f".done in {time.time()-tt:2.2f}s")

    return date_str


def update_loop(ip, port, debug=False):
    with connect(f"ws://{ip}:{port}/", subprotocols=["Lux_WS"]) as ws:
        menu = call(ws, "LOGIN;999999")
        menu_id = menu.find(string="Informationen").parent.parent.attrs["id"]

        id_map = select(ws, menu_id)
        fieldnames = (
            ["time"] + 
            [field for field, unit in variable_mapping.values()] +
            ["status"] 
            )
        

        old_date_str = update_existing_file(fieldnames)

        # wait until next full interval before first sync
        if not debug:
            time.sleep(log_interval - (time.localtime().tm_sec % log_interval))

        # update data
        while True:
            now = time.time()
            now_str = time.strftime("%H:%M:%S", time.localtime(now))
            date_str = time.strftime("%y-%m-%d", time.localtime(now))
            
            # try:
            data = update(ws, id_map)
            print(f"update of data in {time.time()-now:2.2f}s")
            filename = f"data/log_{date_str}.csv"
            with open(filename, mode="a") as f:
                writer = DictWriter(f, fieldnames)
                if date_str != old_date_str:
                    # new file was started we need to output the header
                    writer.writeheader()
                    old_date_str = date_str

                row = dict(time=now_str)
                
                state = 0
                for section, param, value in data:
                    var = f"{section}/{param}"
                    # print(f"{section}/{param}")
                    if var in variable_mapping:
                        field, unit = variable_mapping[var]
                        
                        value = value.replace(unit, "")
                        if var not in non_numeric_var:
                            
                            try:
                                value = float(value)
                            except:
                                value = ''    
                        row[field] = value
                        
                    if var in status_mapping.keys():
                        exp = status_vars.index(var)
                        if value not in status_mapping[var].keys():
                            print(f"{var, value} not found")
                        state_part = status_mapping[var][value]
                        state += state_part * (10**exp)
                        
                code = str(state).zfill(len(status_vars))
                row['status'] = code

                writer.writerow(row)
                print(f".done in {time.time()-now:2.2f}s")

            

            t_calc = time.time() - now
            time.sleep(log_interval - t_calc)

def print_current_state(ip, port):
    with connect(f"ws://{ip}:{port}/", subprotocols=["Lux_WS"]) as ws:
        menu = call(ws, "LOGIN;999999")
        menu_id = menu.find(string="Informationen").parent.parent.attrs["id"]

        id_map = select(ws, menu_id)
        fieldnames = ["time"] + [field for field, unit in variable_mapping.values()]

        # old_date_str = update_existing_file(fieldnames)

        # wait until next full interval before first sync
        # time.sleep(log_interval - (time.localtime().tm_sec % log_interval))

        # update data
        # while True:
        now = time.time()
        now_str = time.strftime("%H:%M:%S", time.localtime(now))
        date_str = time.strftime("%y-%m-%d", time.localtime(now))

        data = update(ws, id_map)
        print(f"update of data in {time.time()-now:2.2f}s")
        # filename = f"data/log_{date_str}.csv"
        # with open(filename, mode="a") as f:
            # writer = DictWriter(f, fieldnames)
            # if date_str != old_date_str:
            #     # new file was started we need to output the header
            #     writer.writeheader()
            #     old_date_str = date_str

        row = dict(time=now_str)
        for section, param, value in data:
            var = f"{section}/{param}"
            print(f"{section}/{param}", value)


def main(ip="192.168.2.254", port=8214, debug=False):
    os.makedirs("data", exist_ok=True)
    while True:  # always restart after error
        try:
            update_loop(ip, port)
        except Exception:
            print(f"Warning: Update loop failed at {pd.Timestamp.now()}")
            print(traceback.format_exc())


if __name__ == "__main__":
    main(debug=True)
    # print_current_state(ip="192.168.2.254", port=8214)
    # update_loop(ip="192.168.2.254", port=8214, debug =True)
