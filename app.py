import os
import time
import traceback
from bs4 import BeautifulSoup
from websockets.sync.client import ClientConnection, connect
import pandas as pd
import numpy as np
#%% config
n_save =1
log_sleep = 60

non_numeric_var = ['Anlagenstatus/Betriebszustand']
variable_mapping = { 
    "Temperaturen/Warmwasser-Ist" : ('Tw Warmasser-Ist', '°C'),
    "Temperaturen/Warmwasser-Soll" : ('Tw Warmwasser-Soll', '°C'),
    "Temperaturen/Außentemperatur" : ('Ta Außentemperatur', '°C'),
    'Temperaturen/Vorlauf'  : ('Th Vorlauf-Ist', '°C'),
    'Temperaturen/Rücklauf' : ('Th Rücklauf-Ist', '°C'),
    'Temperaturen/Rückl.-Soll' : ('Th Rücklauf-Soll', '°C'),
    "Temperaturen/Mischkreis1-Vorlauf" :("Th Mischkreis1-Vorlau-Ist", "°C" ),
    "Temperaturen/Mischkreis1 VL-Soll" :("Th Mischkreis1-VL-Soll", "°C" ),
    "Temperaturen/VD-Heizung" : ("Th VD-Heizung" , '°C'),
    "Temperaturen/Ansaug VD" : ("Temperaturen/Ansaug VD", "°C"),
    "Wärmequelle-Ein" : ("Wärmequelle-Ein", "°C"),
    
    "Anlagenstatus/Betriebszustand" : ("Betriebszustand", ''),
    'Anlagenstatus/Heizleistung Ist' : ('Heizleistung Ist', 'kW'),
    'Anlagenstatus/Abtaubedarf' : ('Abtaubedarf', '%'),
    
    "Wärmemenge/Heizung" :  ("Wärmemenge_Heizung","kWh"),
    "Wärmemenge/Warmwasser" : ("Wärmemenge_Warmwasser", "kWh"),
    # "Wärmemenge/Gesamt" :  ("kWh"),
    "Eingesetzte Energie/Heizung" :  ("Eingesetzte Energie_Heizung", "kWh"),
    "Eingesetzte Energie/Warmwasser" :  ("Eingesetzte Energie_Warmwasser", "kWh"),
    # "Eingesetzte Energie/Gesamt" =:  ("kWh"),
    "Durchfluss" : ("Durchfluss", "l/h")
    }


#%%
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

def update_loop(ip, port):
    with connect(f"ws://{ip}:{port}/", subprotocols=["Lux_WS"]) as ws:
        menu = call(ws, "LOGIN;999999")
        menu_id = menu.find(string="Informationen").parent.parent.attrs["id"]
    
        id_map = select(ws, menu_id)
        i_save=0
        now = pd.Timestamp.now()
        filename = f'data/log_{now.strftime("%y-%m-%d")}.csv'
        if os.path.exists(filename):
            tt = time.time()
            print('Loading from disk..', end='')
            df = pd.read_csv(filename, index_col=0)
            print(f'.done in {time.time()-tt:2.2f}s')
            old_day = now.strftime('%d')
            
            missing_cols = set([x[0] for x in variable_mapping.values()]).difference(df.columns)
            
            for col in missing_cols:
                print(f'Adding column {col}')
                df[col] = np.nan
        else:
            df = pd.DataFrame(columns = [x[0] for x in variable_mapping.values()])
            old_day = 'startup'
        # update data
        
        
        
        while True:
            tt_start = time.time()
            i_save +=1
            now = pd.Timestamp.now()
            now_str = now.strftime('%H:%M:%S') #ToDo .round('min')
            day = now.strftime('%d')
            
            data = update(ws, id_map)
            
            if day != old_day:
                # start new dataframe for new day
                df = pd.DataFrame(columns = [x[0] for x in variable_mapping.values()])
                old_day = day
            
            df.loc[now_str,:] = 0.
            
            for section, param, value in data:
                var = f"{section}/{param}"
                # print(f"{var} = {value}")
                # continue
                # sdf
                
                if var in variable_mapping.keys():
                    # print(f"{var} = {value}")
                    
                    if var in non_numeric_var :
                        df.loc[now_str,variable_mapping[var][0]] = value.replace(variable_mapping[var][1],'')
            
                    else:
                        df.loc[now_str,variable_mapping[var][0]] = float(value.replace(variable_mapping[var][1],''))
            
            if i_save ==n_save:
                tt = time.time()
                print('saving to disk..', end='')
                i_save = 0
                filename = f'data/log_{now.strftime("%y-%m-%d")}.csv'
                df.to_csv(filename)
                print(f'.done in {time.time()-tt:2.2f}s')
                
            t_calc = time.time()-tt_start
            time.sleep(log_sleep -t_calc)

def main(ip="192.168.2.254", port=8214):
    os.makedirs('data', exist_ok=True)
    while True: #always restart after error
    
        try:
            update_loop(ip, port)
        except Exception:
            print(f'Warning: Update loop failed at {pd.Timestamp.now()}')
            print(traceback.format_exc())


if __name__ == "__main__":
    main()
