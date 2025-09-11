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

class globalApplicationPool(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="globalApplicationPool",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_global_application_pools(host, port, token, page) -> List[globalApplicationPool]:
        globalApplicationPools = []
        size = 1000
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v2/global-application-entitlements?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            logger.info(str(len(response_data)) + " globalApplicationPools in page: " + str(page))
            for obj in response_data:
                # creating object and adding it to the result set
                new_pool = globalApplicationPool(obj["name"], obj["id"])
                new_pool.with_property("id", obj["id"])
                new_pool.with_property("scope", obj["scope"])
                new_pool.with_metric("enabled", obj["enabled"])
                globalApplicationPools.append(new_pool)
            if len(response_data) == size:
                get_global_application_pools(host, port, token, page +1)
        else:
            logger.error("Error:", status_code)

        return globalApplicationPools