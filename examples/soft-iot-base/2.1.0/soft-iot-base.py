import time
import timeit
import json
from urllib.request import urlopen
from typing import Optional
from os import popen
from re import sub

from mininet.log import setLogLevel

from fogbed.emulation import Services
from fogbed.experiment.local import FogbedExperiment
from fogbed.node.container import Container
from fogbed.resources.flavors import Resources
from fogbed.resources.models import EdgeResourceModel, FogResourceModel

setLogLevel('info')

def __wait_url(url: str, is_device: bool, timeout: int):
    """ Wait until the webpage of all devices connected to the gateway are 
    available. Which indicates that the gateway has been properly initialized.

    Parameters
    ----------
    url: :class:`str`
        The webpage to check all devices connected to the gateway.
    is_device: :class:`bool`
        If it is init_device function using this function.
    timeout: :class:`int`
        Maximum time in seconds to wait.
    """

    result = None
    start_time = timeit.default_timer()

    while (result == None):
        if (timeit.default_timer() - start_time > timeout):
            raise Exception("URL timeout.")

        time.sleep(2)

        try:
            result = urlopen(url)

            if (is_device):
                try:
                    resp = json.load(result)

                    if ("sensors" not in resp):
                        result = None
                except:
                    result = None
        except:
            pass

    return timeit.default_timer() - start_time


def init_gateway(gateway: Container, ip: str, has_nodes: bool = False, ip_up: Optional[str] = None) -> str:
    """ Initializes the gateway.

    Parameters
    ----------
    gateway: :class:`Container`
        The gateway that will be initialized.
    ip: :class:`str`
        Gateway IP address.
    has_nodes: :class:`bool`
        Indicates whether the gateway will be a parent node(true) or a 
        children node(false).
    ip_up: :class:`str`
        Gateway IP address located in the layer above.
    
    Return
    ------
    url: :class:`str`
        The webpage to check all devices connected to the gateway.
    """

    started: bool = False
    attempt: int = 0
    total_time: float = 0
    timeout: int = 80
    url: str = f"http://localhost:{gateway.params['port_bindings'][8181]}/cxf/iot-service/devices/"

    print("# Starting Karaf")

    while (not started and attempt < 2):
        attempt += 1

        try:
            gateway.cmd("./install.sh &")

            gateway.cmd('$KARAF_HOME/bin/client "feature:repo-add camel 3.11.7"')
            gateway.cmd('$KARAF_HOME/bin/client "feature:install camel-blueprint"')
            gateway.cmd('$KARAF_HOME/bin/client "bundle:install -s mvn:org.codehaus.jackson/jackson-jaxrs/1.9.2 mvn:org.codehaus.jackson/jackson-core-asl/1.9.2 mvn:org.codehaus.jackson/jackson-mapper-asl/1.9.2 "')
            gateway.cmd('$KARAF_HOME/bin/client "bundle:install -s file:/opt/bundles/soft-iot-mapping-devices-1.0.0.jar"')
            gateway.cmd('$KARAF_HOME/bin/client "bundle:install -s file:/opt/bundles/soft-iot-local-storage-1.0.0.jar"')
            gateway.cmd('$KARAF_HOME/bin/client "bundle:install -s file:/opt/bundles/soft-iot-iot-service-1.0.0.jar"')
            gateway.cmd('$KARAF_HOME/bin/client "bundle:install -s file:/opt/bundles/SOFT-IoT-DLT-Auth-1.0-SNAPSHOT.jar"')

            total_time += round(__wait_url(url, False, timeout), 1)

            print(
                f"## Karaf started in {total_time}s in {attempt} attempt(s)")
            
            started = True
        except:
            total_time += timeout

    if (not started):
        raise Exception("URL timeout.")

    return url


def init_device(device: Container, gateway_ip: str, url: str) -> None:
    """ Initializes the virtual fot device.

    Parameters
    ----------
    device: :class:`Container`
        The device that will be initialized.
    gateway_ip: :class:`str`
        IP address of the gateway to which the device will connect.
    url: :class:`str`
        The webpage to check all devices connected to the gateway.
    """

    started: bool = False
    attempt: int = 0
    total_time: float = 0
    timeout: int = 15

    print(f"# Starting {device.name}")

    while (not started and attempt < 3):
        attempt += 1

        try:
            device.cmd(f"java -jar device.jar -di {device.name} -bi {gateway_ip} &")

            total_time += round(
                __wait_url(f"{url}{device.name}", True, timeout), 1)

            print(
                f"## Device {device.name} started in {total_time}s in {attempt} attempt(s)")

            started = True
        except:
            total_time += timeout

    if (not started):
        raise Exception("URL timeout.")

def get_container_ip(container_name: str) -> str:
    """ Get the IP address of a docker container by name.

    Parameters
    ----------
    container_name: :class:`str`
        Container name.

    Return
    ------
    :class:`str`
    """

    output: str = popen(f"docker exec mn.{container_name} cat /etc/hosts | grep {container_name}").readlines()[0]
    
    output_sanitized: str = sub(r"[^(\d|\.)]", "", output)

    return output_sanitized


Services(max_cpu=6, max_mem=6144)

exp = FogbedExperiment()

fog = exp.add_virtual_instance(
    f'fog', FogResourceModel(max_cu=32, max_mu=4096))

edge = exp.add_virtual_instance(
    f'edge', EdgeResourceModel(max_cu=20, max_mu=2048))

gateway_fog = Container(
    f'gat_fog',
    resources=Resources.XLARGE,
    dimage="larsid/soft-iot-base:2.1.0-fogbed",
    port_bindings={1883: 1883, 8181: 8181, 1099: 1099,
                   8101: 8101, 61616: 61616, 44444: 44444}
)

device_1 = Container(f'device_1', resources=Resources.SMALL,
                     dimage='larsid/virtual-fot-device:1.0.0-fogbed')

exp.add_docker(gateway_fog, fog)
exp.add_docker(device_1, edge)

exp.add_link(fog, edge)

try:
    exp.start()

    gateway_fog_ip: str = get_container_ip(gateway_fog.name)

    gateway_fog_url: str = init_gateway(gateway=gateway_fog, ip=gateway_fog_ip, has_nodes=False)

    init_device(device_1, gateway_fog_ip, gateway_fog_url)

    input("\nPress ENTER to finish...")
    exp.stop()
except Exception as e:
    print(e)
