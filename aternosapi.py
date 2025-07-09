import cloudscraper
import asyncio
from bs4 import BeautifulSoup

class AternosAPI:
    def __init__(self, headers, TOKEN, timeout=10):  # <-- Cambiado a __init__
        self.timeout = timeout
        self.headers = {}
        self.TOKEN = TOKEN
        self.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0"
        self.headers['Cookie'] = headers
        self.SEC = self.getSEC()
        self.JavaSoftwares = ['Vanilla', 'Spigot', 'Forge', 'Magma','Snapshot', 'Bukkit', 'Paper', 'Modpacks', 'Glowstone']
        self.BedrockSoftwares = ['Bedrock', 'Pocketmine-MP']

    def getSEC(self):
        headers = self.headers['Cookie'].split(";")
        for sec in headers:
            if sec.strip().startswith("ATERNOS_SEC_"):
                sec = sec.split("_")
                if len(sec) == 3:
                    sec = ":".join(sec[2].split("="))
                    return sec
        print("Invalid SEC")
        exit(1)

    async def GetStatus(self):
        webserver = await self.filterCloudflare(url='https://aternos.org/server/', headers=self.headers)
        webdata = BeautifulSoup(webserver.text, 'html.parser')
        status = webdata.find('span', class_='statuslabel-label').text
        status = status.strip()
        return status

    async def StartServer(self):
        serverstatus = await self.GetStatus()
        print(f"[DEBUG] Estado inicial: {serverstatus}")
        if serverstatus == "Online":
            return "Server Already Running"
        else:
            parameters = {'headstart': 0, 'SEC': self.SEC, 'TOKEN': self.TOKEN}
            resp = await self.filterCloudflare(url="https://aternos.org/panel/ajax/start.php", params=parameters, headers=self.headers)
            print(f"[DEBUG] Respuesta start.php: {resp.text[:200]}")
            while "Preparing" not in await self.GetStatus() and await self.GetStatus() != "Online":
                await asyncio.sleep(10)
                resp2 = await self.filterCloudflare(url="https://aternos.org/panel/ajax/confirm.php", params=parameters, headers=self.headers)
                print(f"[DEBUG] Respuesta confirm.php: {resp2.text[:200]}")
            return "Server Started"

    async def StopServer(self):
        serverstatus = await self.GetStatus()
        if serverstatus == "Offline":
            return "Server Already Offline"
        else:
            parameters = {'SEC': self.SEC, 'TOKEN': self.TOKEN}
            await self.filterCloudflare(url="https://aternos.org/panel/ajax/stop.php", params=parameters, headers=self.headers)
            return "Server Stopped"

    async def GetServerInfo(self):
        ServerInfo = await self.filterCloudflare(url='https://aternos.org/server/', headers=self.headers)
        ServerInfo = BeautifulSoup(ServerInfo.text, 'html.parser')
        Software = ServerInfo.find('span', id='software')
        if not Software:
            return
        Software = Software.text.strip()
        if self.arrayContains(self.JavaSoftwares, Software):
            IP = ServerInfo.find('div', class_='server-ip mobile-full-width').get_text().strip().split(" ")[0]
            Port = "25565(Optional)"
            return f"{IP},{Port},{Software}"
        elif self.arrayContains(self.BedrockSoftwares, Software):
            IP = ServerInfo.find('span', id='ip').get_text().strip()
            Port = ServerInfo.find('span', id='port').get_text().strip()
            return f"{IP},{Port},{Software}"

    async def filterCloudflare(self, url, params=None, headers=None):
        loop = asyncio.get_event_loop()
        def make_request():
            requests = cloudscraper.create_scraper()
            gotData = requests.get(url, params=params, headers=headers)
            counter = 0
            while "<title>Please Wait... | Cloudflare</title>" in gotData.text and counter < self.timeout:
                requests = cloudscraper.create_scraper()
                import time; time.sleep(1)
                gotData = requests.get(url, params=params, headers=headers)
                counter += 1
            if "<title>Please Wait... | Cloudflare</title>" in gotData.text:
                print("Cloudflare error!!")
                exit(0)
            return gotData
        return await loop.run_in_executor(None, make_request)

    def arrayContains(self, array, string):
        for i in array:
            if string.lower() in i.lower() or i.lower() in string.lower():
                return True
        return False

