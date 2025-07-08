import os
import time
import traceback
from csv import DictWriter

import jq
import pandas as pd
from websockets.sync.client import ClientConnection, connect

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
    "Temperaturen/Wärmequelle-Ein": ("Wärmequelle-Ein", "°C"),
    "Anlagenstatus/Betriebszustand": ("Betriebszustand", ""),
    "Anlagenstatus/Heizleistung Ist": ("Heizleistung Ist", "kW"),
    "Anlagenstatus/Abtaubedarf": ("Abtaubedarf", "%"),
    "Energiemonitor/Wärmemenge/Heizung": ("Wärmemenge_Heizung", "kWh"),
    "Energiemonitor/Wärmemenge/Warmwasser": ("Wärmemenge_Warmwasser", "kWh"),
    # "Wärmemenge/Gesamt" :  ("kWh"),
    "Energiemonitor/Leistungsaufnahme/Heizung": ("Eingesetzte Energie_Heizung", "kWh"),
    "Energiemonitor/Leistungsaufnahme/Warmwasser": (
        "Eingesetzte Energie_Warmwasser",
        "kWh",
    ),
    # "Eingesetzte Energie/Gesamt" =:  ("kWh"),
    "Eingänge/Durchfluss": ("Durchfluss", "l/h"),
}

status_mapping = {
    "Anlagenstatus/Betriebszustand": {"": 0, "Heizen": 1, "WW": 1, "ABT": 2},
    "Eingänge/STB E-Stab": {"Aus": 0, "Ein": 1},
    "Ausgänge/HUP": {"Aus": 0, "Ein": 1},
    "Ausgänge/BUP": {"Aus": 0, "Ein": 1},
    "Ausgänge/Verdichter": {"Aus": 0, "Ein": 1},
    "Ausgänge/VD-Heizung": {"Aus": 0, "Ein": 1},
}

status_vars = list(status_mapping.keys())


# %%
def call(ws: ClientConnection, cmd) -> str:
    ws.send(cmd)
    return ws.recv(timeout=10)


def select(ws: ClientConnection, id: str) -> dict[str, tuple]:
    id_map = {}
    info_items = call(ws, f"GET;{id}")
    values = jq.all(
        """
            def flatten($path):
                if has("items") then
                    .items[] | flatten($path + "/" + .name)
                else
                    {name: $path, id}
                end;

            .items[] | flatten(.name)
        """,
        text=info_items,
    )
    id_map = {v["id"]: v["name"] for v in values}

    return id_map


def update(ws: ClientConnection, id_map) -> list[tuple]:
    data = []
    for it in jq.all('.. | select(try has("value"))', text=call(ws, "REFRESH")):
        data.append((id_map[it["id"]], it["value"]))
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
    print(f".done in {time.time() - tt:2.2f}s")

    return date_str


def update_loop(ip, port, debug=False):
    with connect(f"ws://{ip}:{port}/", subprotocols=["Lux_WS"]) as ws:
        menu = call(ws, "LOGIN;999999")
        menu_id = jq.first(
            '.items[] | select(.name == "Informationen") | .id', text=menu
        )

        id_map = select(ws, menu_id)
        fieldnames = (
            ["time"] + [field for field, unit in variable_mapping.values()] + ["status"]
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

            data = update(ws, id_map)
            print(f"update of data in {time.time() - now:2.2f}s")
            filename = f"data/log_{date_str}.csv"
            with open(filename, mode="a") as f:
                writer = DictWriter(f, fieldnames)
                if date_str != old_date_str:
                    # new file was started we need to output the header
                    writer.writeheader()
                    old_date_str = date_str

                row = dict(time=now_str)

                state = 0

                for var, value in data:
                    if var in variable_mapping:
                        field, unit = variable_mapping[var]

                        value = value.replace(unit, "")
                        if var not in non_numeric_var:
                            try:
                                value = float(value)
                            except ValueError:
                                value = ""
                        row[field] = value

                    if var in status_mapping:
                        exp = status_vars.index(var)
                        if value not in status_mapping[var].keys():
                            print(f"{var, value} not found")
                        state_part = status_mapping[var][value]
                        state += state_part * (10**exp)

                code = str(state).zfill(len(status_vars))
                row["status"] = code

                writer.writerow(row)
                print(f".done in {time.time() - now:2.2f}s")

            t_calc = time.time() - now
            time.sleep(log_interval - t_calc)


def main(ip="192.168.2.254", port=8214, debug=False):
    os.makedirs("data", exist_ok=True)
    while True:  # always restart after error
        try:
            update_loop(ip, port)
        except Exception:
            print(f"Warning: Update loop failed at {pd.Timestamp.now()}")
            print(traceback.format_exc())
            time.sleep(30)


if __name__ == "__main__":
    main(debug=True)
    # print_current_state(ip="192.168.2.254", port=8214)
    # update_loop(ip="192.168.2.254", port=8214, debug =True)
