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

from restcall import RestClient

logger = logging.getLogger(__name__)

class globalDesktopPool(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="globalDesktopPool",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_global_desktop_pools(host, port, token, page) -> List[globalDesktopPool]:
        size = 1000
        globalDesktopPools = []
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v1/global-desktop-entitlements?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            for obj in response_data:
                logger.info("Pool ID:" + obj["id"])
                logger.info("Pool Name:" + obj["name"])
                # creating object and adding it to the result set
                new_pool = globalDesktopPool(obj["name"], obj["id"])
                new_pool.with_property("id", obj["id"])
                new_pool.with_metric("enabled", obj["enabled"])
                globalDesktopPools.append(new_pool)
            if len(response_data) == size:
                get_global_desktop_pools(host, port, token, page +1)
        else:
            logger.error("Error:", status_code)

        return globalDesktopPools