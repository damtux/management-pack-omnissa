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
from globalDesktopPools import globalDesktopPool

from restcall import RestClient

logger = logging.getLogger(__name__)

class localDesktopPool(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="localDesktopPool",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_local_desktop_pools(host, port, token, page, globalDesktopPools: List[globalDesktopPool]) -> List[localDesktopPool]:
        localDesktopPools = []
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        size = 1000
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v6/desktop-pools?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            logger.info(str(len(response_data)) + " localDesktopPools in page: " + str(page))
            for obj in response_data:
                # creating object and adding it to the result set
                new_localDesktopPool = localDesktopPool(obj["name"], obj["id"])
                new_localDesktopPool.with_property("id", obj["id"])
                new_localDesktopPool.with_metric("enabled", obj["enabled"])
                if "global_desktop_entitlement_id" in obj:
                    new_localDesktopPool.with_property("global_pool_id", obj["global_desktop_entitlement_id"])
                    for globalPool in globalDesktopPools:
                        if globalPool.id == obj["global_desktop_entitlement_id"]:
                            new_localDesktopPool.add_parent(globalPool)
                localDesktopPools.append(new_localDesktopPool)
            if len(response_data) == size:
                get_local_desktop_pools(host, port, token, page +1, globalDesktopPools)
        else:
            logger.error("Error:", status_code)

        return localDesktopPools