import time

from bs4 import BeautifulSoup
from websockets.sync.client import ClientConnection, connect


def call(ws: ClientConnection, cmd) -> BeautifulSoup:
    ws.send(cmd)
    return BeautifulSoup(ws.recv(timeout=10), "html.parser")


def select(ws: ClientConnection, id: str) -> dict[str, tuple]:
    id_map = {}
    info_items = call(ws, f"GET;{id}")
    section_items = info_items.find(name="content").find_all("item", recursive=False)
    for section_it in section_items:
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


def main(ip="192.168.2.254", port=8214):
    with connect(f"ws://{ip}:{port}/", subprotocols=["Lux_WS"]) as ws:
        menu = call(ws, "LOGIN;999999")
        menu_id = menu.find(string="Informationen").parent.parent.attrs["id"]

        id_map = select(ws, menu_id)
        #
        # update data
        while True:
            data = update(ws, id_map)
            for section, param, value in data:
                print(f"{section}/{param} = {value}")

            time.sleep(10)

        # section_items.find_all("item")


if __name__ == "__main__":
    main()
