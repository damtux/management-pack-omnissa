import aria.ops.adapter_logging as logging
import constants
import json
from constants import ADAPTER_KIND
from aria.ops.object import Object
from typing import List
from aria.ops.data import Metric
from aria.ops.data import Property
from aria.ops.object import Identifier
from aria.ops.object import Key
from RDSFarms import RDSFarm
from globalApplicationPools import globalApplicationPool

from restcall import RestClient

logger = logging.getLogger(__name__)

class localApplicationPool(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="localApplicationPool",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_local_application_pools(host, port, token, page, RDSFarms: List[RDSFarm], globalApplicationPools: List[globalApplicationPool]) -> List[localApplicationPool]:
        localApplicationPools = []
        size = 1000
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v3/application-pools?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            logger.info(str(len(response_data)) + " localApplicationPools in page: " + str(page))
            for obj in response_data:
                # creating object and adding it to the result set
                new_pool = localApplicationPool(obj["name"], obj["id"])
                new_pool.with_property("id", obj["id"])
                new_pool.with_metric("enabled", obj["enabled"])
                if "farm_id" in obj:
                    new_pool.with_property("farm_id", obj["farm_id"])
                    for RDSFarm in RDSFarms:
                        if RDSFarm.id == obj["farm_id"]:
                            new_pool.add_child(RDSFarm)
                if "global_application_entitlement_id" in obj:
                    new_pool.with_property("global_pool_id", obj["global_application_entitlement_id"])
                    for globalApplicationPool in globalApplicationPools:
                        if globalApplicationPool.id == obj["global_application_entitlement_id"]:
                            new_pool.add_parent(globalApplicationPool)
                localApplicationPools.append(new_pool)
            if len(response_data) == size:
                get_local_application_pools(host, port, token, page +1, RDSFarms, globalApplicationPools)
        else:
            logger.error("Error:", status_code)

        return localApplicationPools