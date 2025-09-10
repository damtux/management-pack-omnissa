#  Copyright 2022 VMware, Inc.
#  SPDX-License-Identifier: Apache-2.0
import json
import sys
from typing import List
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import aria.ops.adapter_logging as logging
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.data import Metric
from aria.ops.data import Property
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.definition.units import Units
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.timer import Timer

import constants
from constants import ADAPTER_KIND
from constants import ADAPTER_NAME
from constants import HOST_IDENTIFIER
from constants import PORT_IDENTIFIER
from constants import USER_CREDENTIAL
from constants import PASSWORD_CREDENTIAL
from constants import DOMAIN_CREDENTIAL
from restcall import RestClient
from collectDevices import DeviceCollector

logger = logging.getLogger(__name__)

def get_adapter_definition() -> AdapterDefinition:
    """
    The adapter definition defines the object types and attribute types (metric/property) that are present
    in a collection. Setting these object types and attribute types helps VMware Aria Operations to
    validate, process, and display the data correctly.
    :return: AdapterDefinition
    """
    with Timer(logger, "Get Adapter Definition"):
        definition = AdapterDefinition(ADAPTER_KIND, ADAPTER_NAME)

        definition.define_int_parameter(
            "container_memory_limit",
            label="Adapter Memory Limit (MB)",
            description="Sets the maximum amount of memory VMware Aria Operations can "
            "allocate to the container running this adapter instance.",
            required=True,
            advanced=True,
            default=1024,
        )

        definition.define_string_parameter(
            constants.HOST_IDENTIFIER,
            label="Host",
            description="FQDN or IP of one Omnissa connection server",
            required=True,
            default="",
        )

        definition.define_int_parameter(
            constants.PORT_IDENTIFIER,
            label="TCP Port",
            description="TCP Port Omnissa is listening on",
            required=True,
            advanced=True,
            default=443,
        )
        
        credential = definition.define_credential_type("vdi_user", "Credential")
        credential.define_string_parameter(constants.USER_CREDENTIAL, "User Name") 
        credential.define_password_parameter(constants.PASSWORD_CREDENTIAL, "Password")
        credential.define_string_parameter(constants.DOMAIN_CREDENTIAL, "Domain")

    # Object types definition section

        pool = definition.define_object_type("pool", "pool")
        pool.define_string_property("id", "id")
        pool.define_string_property("name", "name")
        pool.define_metric("enabled", "enabled")

        logger.debug(f"Returning adapter definition: {definition.to_json()}")
        return definition

def test(adapter_instance: AdapterInstance) -> TestResult:
    with Timer(logger, "Test"):
        result = TestResult()
        try:
            host = adapter_instance.get_identifier_value(constants.HOST_IDENTIFIER)
            port = adapter_instance.get_identifier_value(constants.PORT_IDENTIFIER)
            base_url = "https://" + str(host) + ":" + str(port)
            user = adapter_instance.get_credential_value(constants.USER_CREDENTIAL)
            password = adapter_instance.get_credential_value(constants.PASSWORD_CREDENTIAL)
            domain = adapter_instance.get_credential_value(constants.DOMAIN_CREDENTIAL)

            logger.info(f"URL: {base_url}") 
            headers = {
                'Content-Type': 'application/json',
                'Accept': '*/*',
            }

            payload = {
                "username": user,
                "password": password,
                "domain": domain,
            }
            json_payload = json.dumps(payload)

            client = RestClient(base_url)
            status_code, response_data = client.post("/rest/login", headers, json_payload)
            if status_code == 200:
                token = response_data.get("access_token")
            else:
                logger.error("Error:", status_code)

            client = None
            headers = None
            headers = {
                'Authorization': 'Bearer ' + token,
            }
            client = RestClient(base_url)
            status_code, response_data = client.get("/rest/inventory/v1/desktop-pools", headers)            

            return result
            # Sample test connection code follows. Replace with your own test connection
            # code. A typical test connection will generally consist of:
            # 1. Read identifier values from adapter_instance that are required to
            #    connect to the target(s)
            # 2. Connect to the target(s), and retrieve some sample data
            # 3. Disconnect cleanly from the target (ensure this happens even if an
            #    error occurs)
            # 4. If any of the above failed, return an error, otherwise pass.

            # Read the 'ID' identifier in the adapter instance and use it for a
            # connection test.
            #id = adapter_instance.get_identifier_value("ID")

            # In this case the adapter does not need to connect
            # to anything, as it reads directly from the host it is running on.
            #if id is None:
            #    result.with_error("No ID Found")
            #elif id.lower() == "bad":
                # As there is not an actual failure condition to test for, this
                # example only shows the mechanics of reading identifiers and
                # constructing test results. Here we add an error to the result
                # that is returned.
            #    result.with_error("The ID is bad")
            # otherwise, the test has passed
        except Exception as e:
            logger.error("Unexpected connection test error")
            logger.exception(e)
            result.with_error("Unexpected connection test error: " + repr(e))
        finally:
            # TODO: If any connections are still open, make sure they are closed before returning
            logger.debug(f"Returning test result: {result.get_json()}")
            return result


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        try:
            host = adapter_instance.get_identifier_value(constants.HOST_IDENTIFIER)
            port = adapter_instance.get_identifier_value(constants.PORT_IDENTIFIER)
            base_url = "https://" + str(host) + ":" + str(port)
            logger.info(base_url)

            user = adapter_instance.get_credential_value(constants.USER_CREDENTIAL)
            password = adapter_instance.get_credential_value(constants.PASSWORD_CREDENTIAL)
            domain = adapter_instance.get_credential_value(constants.DOMAIN_CREDENTIAL)

            headers = {
                'Content-Type': 'application/json',
                'Accept': '*/*',
            }
            payload = {
                "username": user,
                "password": password,
                "domain": domain, 
            }

            json_payload = json.dumps(payload)
            logger.info(json_payload)
            client = RestClient(base_url)
            status_code, response_data = client.post("/rest/login", headers, json_payload)
            logger.info(status_code)
            if status_code == 200:
                token = response_data.get("access_token")
            else:
                logger.error("Error:", status_code)
            
            logger.info(token)

            devicecollector = DeviceCollector(adapter_instance, token, host, result, logger)

            result = devicecollector.collect()

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            # TODO: If any connections are still open, make sure they are closed before returning
            logger.debug(f"Returning collection result {result.get_json()}")
            return result


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        result = EndpointResult()
        # In the case that an SSL Certificate is needed to communicate to the target,
        # add each URL that the adapter uses here. Often this will be derived from a
        # 'host' parameter in the adapter instance. In this Adapter we don't use any
        # HTTPS connections, so we won't add any. If we did, we might do something like
        # this:
        # result.with_endpoint(adapter_instance.get_identifier_value("host"))
        #
        # Multiple endpoints can be returned, like this:
        # result.with_endpoint(adapter_instance.get_identifier_value("primary_host"))
        # result.with_endpoint(adapter_instance.get_identifier_value("secondary_host"))
        #
        # This 'get_endpoints' method will be run before the 'test' method,
        # and VMware Aria Operations will use the results to extract a certificate from
        # each URL. If the certificate is not trusted by the VMware Aria Operations
        # Trust Store, the user will be prompted to either accept or reject the
        # certificate. If it is accepted, the certificate will be added to the
        # AdapterInstance object that is passed to the 'test' and 'collect' methods.
        # Any certificate that is encountered in those methods should then be validated
        # against the certificate(s) in the AdapterInstance.
        logger.debug(f"Returning endpoints: {result.get_json()}")
        return result


# Main entry point of the adapter. You should not need to modify anything below this line.
def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    # Start a new log file by calling 'rotate'. By default, the last five calls will be
    # retained. If the logs are not manually rotated, the 'setup_logging' call should be
    # invoked with the 'max_size' parameter set to a reasonable value, e.g.,
    # 10_489_760 (10MB).
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        # `inputfile` and `outputfile` are always automatically appended to the
        # argument list by the server
        logger.error("Arguments must be <method> <inputfile> <ouputfile>")
        sys.exit(1)

    method = argv[0]
    try:
        if method == "test":
            test(AdapterInstance.from_input()).send_results()
        elif method == "endpoint_urls":
            get_endpoints(AdapterInstance.from_input()).send_results()
        elif method == "collect":
            collect(AdapterInstance.from_input()).send_results()
        elif method == "adapter_definition":
            result = get_adapter_definition()
            if type(result) is AdapterDefinition:
                result.send_results()
            else:
                logger.info(
                    "get_adapter_definition method did not return an AdapterDefinition"
                )
                sys.exit(1)
        else:
            logger.error(f"Command {method} not found")
            sys.exit(1)
    finally:
        logger.info(Timer.graph())
        sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
