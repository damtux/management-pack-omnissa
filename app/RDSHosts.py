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

from restcall import RestClient

logger = logging.getLogger(__name__)

class RDSHost(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="RDSHost",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_rds_hosts(host, port, token, page, RDSFarms: List[RDSFarm]) -> List[RDSHost]:
        RDSHosts = []
        size = 1000
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v1/rds-servers?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            for obj in response_data:
                logger.info("Host ID:" + obj["id"])
                logger.info("Host Name:" + obj["name"])
                # creating object and adding it to the result set
                new_host = RDSHost(obj["name"], obj["id"])
                new_host.with_property("id", obj["id"])
                new_host.with_metric("enabled", obj["enabled"])
                new_host.with_property("farm_id", obj["farm_id"])
                if "session_count" in obj:
                    new_host.with_metric("session_count", obj["session_count"])
                if "max_sessions_count" in obj:
                    new_host.with_metric("max_session_count", obj["max_sessions_count"])
                if "max_sessions_count_configured" in obj:
                     new_host.with_metric("max_sessions_count_configured", obj["max_sessions_count_configured"])
                new_host.with_metric("state", obj["state"])

                for RDSFarm in RDSFarms:
                        if RDSFarm.id == obj["farm_id"]:
                            new_host.add_parent(RDSFarm)   

                RDSHosts.append(new_host)
            if len(response_data) == size:
                get_rds_hosts(host, port, token, page +1, RDSFarms)
        else:
            logger.error("Error:", status_code)

        return RDSHosts