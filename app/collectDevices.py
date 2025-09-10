import constants
from constants import ADAPTER_KIND
from constants import ADAPTER_NAME
from constants import HOST_IDENTIFIER
from constants import PORT_IDENTIFIER
from constants import USER_CREDENTIAL
from constants import PASSWORD_CREDENTIAL

from restcall import RestClient

class DeviceCollector:
    def __init__(self, adapter_instance, token, fqdn, result, logger):
        self.fqdn = fqdn
        self.token = token
        self.result = result
        self.logger = logger
        self.adapter_instance = adapter_instance

    def collect(self):
        host = self.adapter_instance.get_identifier_value(constants.HOST_IDENTIFIER)
        port = self.adapter_instance.get_identifier_value(constants.PORT_IDENTIFIER)
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + self.token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v1/desktop-pools'
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            for obj in response_data:
                self.logger.info("Pool ID:" + obj["id"])
                self.logger.info("Pool Name:" + obj["name"])
                # creating object and adding it to the result set
                device_obj = self.result.object(ADAPTER_KIND, "pool", obj["name"])
                device_obj.with_property(
                    "id", obj["id"]
                )
                device_obj.with_metric(
                    "enabled", obj["enabled"]
                )
        else:
            self.logger.error("Error:", status_code)

        return self.result

