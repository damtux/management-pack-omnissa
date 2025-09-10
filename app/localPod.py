import aria.ops.adapter_logging as logging
import constants
import json
from constants import ADAPTER_KIND
from globalDesktopPools import globalDesktopPool
from typing import List
from aria.ops.object import Object
from aria.ops.data import Metric
from aria.ops.data import Property
from aria.ops.object import Identifier
from aria.ops.object import Key
from globalApplicationPools import globalApplicationPool

from restcall import RestClient

logger = logging.getLogger(__name__)

class localPod(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="pod",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_local_pod(host, port, token, globalDesktopPools: List[globalDesktopPool], globalApplicationPools: List[globalApplicationPool]) -> List[localPod]:
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        localPods = []
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/federation/v1/pods'
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            for obj in response_data:
                if obj["local_pod"] == True:
                    logger.info("Pod Id:" + obj["id"])
                    logger.info("Pod Name:" + obj["name"])
                    # creating object and adding it to the result set
                    new_localPod = localPod(obj["name"], obj["id"])
                    new_localPod.with_property("id", obj["id"])
                    if "active_global_desktop_entitlements" in obj:
                        for poolId in obj["active_global_desktop_entitlements"]:
                            for globalPool in globalDesktopPools:
                                if poolId == globalPool.id:
                                    new_localPod.add_child(globalPool)
                    if "active_global_application_entitlements" in obj:
                        for poolId in obj["active_global_application_entitlements"]:
                            for globalPool in globalApplicationPools:
                                if poolId == globalPool.id:
                                    new_localPod.add_child(globalPool)
                    localPods.append(new_localPod)
        else:
            logger.error("Error:", status_code)

        return localPods