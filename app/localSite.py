import aria.ops.adapter_logging as logging
import json
import constants
from constants import ADAPTER_KIND
from typing import List
from localPod import localPod
from aria.ops.object import Object
from aria.ops.data import Metric
from aria.ops.data import Property
from aria.ops.object import Identifier
from aria.ops.object import Key

from restcall import RestClient

logger = logging.getLogger(__name__)

class localSite(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="site",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_local_site(host, port, token, localPods: List[localPod]) -> List[localSite]:
        localSites = []
        
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/federation/v1/sites'
        status_code, response_data = client.get(queryString, headers)
        logger.info(json.dumps(response_data))
        for localPod in localPods:
            logger.info('localPod: ' + localPod.id + " | " + localPod.name)
        if status_code == 200:
            for site in response_data:
                logger.info("Site Id:" + site["id"] + " | " + site["name"])
                for podId in site["pods"]:
                    if localPods:
                        for pod in localPods:
                            logger.info('Current Pod: ' + podId)
                            logger.info('Local pod to match: ' + pod.id)
                            if podId == pod.id:
                                logger.info("Local Site Name: " + site["name"])
                                new_site = localSite(site["name"], site["id"])
                                new_site.with_property("id", site["id"])
                                new_site.add_child(pod)
                                localSites.append(new_site)
        else:
            logger.error("Error:", status_code)

        return localSites