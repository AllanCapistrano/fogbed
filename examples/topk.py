import time
import timeit
import json
from urllib.request import urlopen

from mininet.log import setLogLevel

from fogbed.emulation import Services
from fogbed.experiment.local import FogbedExperiment
from fogbed.node.container import Container
from fogbed.resources.flavors import Resources
from fogbed.resources.models import EdgeResourceModel, FogResourceModel

setLogLevel('info')

url = "http://localhost:8181/cxf/iot-service/devices/"
url2 = "http://localhost:8182/cxf/iot-service/devices/" # TODO: Colocar dinamicamente a URL


def wait_url(url, verify, timeout): # TODO: Adicionar comentários
    result = None
    start_time = timeit.default_timer()

    while (result == None):
        if (timeit.default_timer() - start_time > timeout):
            raise Exception("url timeout")

        time.sleep(2)

        try:
            result = urlopen(url)
            if (verify):
                try:
                    resp = json.load(result)
                    if ("device" not in resp):
                        result = None
                except:
                    result = None
        except:
            pass

    return timeit.default_timer() - start_time


def init_gateway(gateway: Container, url: str, has_nodes: bool = False, ip_up: str = None): # TODO: Adicionar comentários
    started = False
    attempt = 0
    total_time = 0
    timeout = 80

    print("# Starting Servicemix")

    while (not started and attempt < 2):
        attempt += 1

        try:
            gateway.cmd(f"IP={gateway.ip}") # Configurando o IP do gateway.

            if(ip_up != None):
                gateway.cmd(f"IP_UP={ip_up}") # Configurando o IP do gateway pai, caso possua.
            
            if(has_nodes):
                gateway.cmd(f"HAS_NODES=true") # Configurando se o gateway possui filhos ou não.

            gateway.cmd("./usr/local/bin/servicemix-init.sh &")
            gateway.cmd("./opt/servicemix/bin/servicemix &")

            total_time += round(wait_url(url, False, timeout), 1)

            print(
                f"## Servicemix started in {total_time}s in {attempt} attempt(s)")
            
            started = True
        except:
            total_time += timeout

    if (not started):
        raise Exception("url timeout")


def init_device(device: Container, gateway_ip: str, url): # TODO: Adicionar comentários
    started = False
    attempt = 0
    total_time = 0
    timeout = 15

    print(f"# Starting {device.name}")

    while (not started and attempt < 3):
        attempt += 1

        try:
            device.cmd(f"java -jar device.jar -di {device.name} -bi {gateway_ip} &")

            total_time += round(
                wait_url(f"{url}{device.name}/temperatureSensor", True, timeout), 1)

            print(
                f"## Device {device.name} started in {total_time}s in {attempt} attempt(s)")

            started = True
        except:
            total_time += timeout

    if (not started):
        raise Exception("url timeout")


Services(max_cpu=6, max_mem=4096)

exp = FogbedExperiment()

fog = exp.add_virtual_instance(
    f'fog', FogResourceModel(max_cu=32, max_mu=1024))

edge = exp.add_virtual_instance(
    f'edge', EdgeResourceModel(max_cu=3, max_mu=1024))

gateway_fog = Container(
    f'gat_fog',
    resources=Resources.XLARGE,
    dimage="larsid/top-k:1.0.0-fogbed",
    port_bindings={1883: 1883, 8181: 8181, 1099: 1099,
                   8101: 8101, 61616: 61616, 44444: 44444}
)
gateway_edge = Container(
    f'gat_edge',
    resources=Resources.XLARGE,
    dimage="larsid/top-k:1.0.0-fogbed",
    port_bindings={1883: 1884, 8181: 8182, 1099: 1100,
                   8101: 8102, 61616: 61617, 44444: 44445}
)

device_1 = Container(f'device_1', resources=Resources.SMALL,
                     dimage='larsid/virtual-fot-device:1.0.0-fogbed')
device_2 = Container(f'device_2', resources=Resources.SMALL,
                     dimage='larsid/virtual-fot-device:1.0.0-fogbed')

exp.add_docker(gateway_fog, fog)
exp.add_docker(gateway_edge, fog) # TODO: Colocar na edge
exp.add_docker(device_1, edge)
exp.add_docker(device_2, edge)

exp.add_link(fog, edge)

try:
    exp.start()

    init_gateway(gateway=gateway_fog, url=url, has_nodes=True)
    init_gateway(gateway=gateway_edge, url=url2, ip_up=gateway_fog.ip)

    init_device(device_1, gateway_fog.ip, url)
    init_device(device_2, gateway_edge.ip, url2)
except Exception as e:
    print(e)

exp.stop()
