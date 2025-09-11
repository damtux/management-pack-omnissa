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
#from collectDevices import
from localSite import get_local_site
from localPod import get_local_pod
from globalDesktopPools import get_global_desktop_pools
from localDesktopPools import get_local_desktop_pools
from localSessions import get_local_sessions
from RDSFarms import get_rds_farms
from RDSHosts import get_rds_hosts
from localApplicationPools import get_local_application_pools
from globalApplicationPools import get_global_application_pools

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
            default=2048,
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

        localSite = definition.define_object_type("site", "Site")
        localSite.define_string_identifier("uuid", "UUID")
        localSite.define_string_property("id", "id")
        localSite.define_string_property("name", "name")

        localPod = definition.define_object_type("pod", "Pod")
        localPod.define_string_identifier("uuid", "UUID")
        localPod.define_string_property("id", "id")
        localPod.define_string_property("name", "name")

        globalDesktopPool = definition.define_object_type("globalDesktopPool", "Global desktop pool")
        globalDesktopPool.define_string_identifier("uuid", "UUID")
        globalDesktopPool.define_string_property("id", "id")
        globalDesktopPool.define_string_property("name", "name")
        globalDesktopPool.define_metric("enabled", "enabled")

        localDesktopPool = definition.define_object_type("localDesktopPool", "Local desktop pool")
        localDesktopPool.define_string_identifier("uuid", "UUID")
        localDesktopPool.define_string_property("id", "id")
        localDesktopPool.define_string_property("name", "name")
        localDesktopPool.define_string_property("global_pool_id", "Global pool")
        localDesktopPool.define_string_property("farm_id", "farm_id")
        localDesktopPool.define_metric("enabled", "enabled")

        globalApplicationPool = definition.define_object_type("globalApplicationPool", "Global application pool")
        globalApplicationPool.define_string_identifier("uuid", "UUID")
        globalApplicationPool.define_string_property("id", "id")
        globalApplicationPool.define_string_property("name", "name")
        globalApplicationPool.define_string_property("scope", "scope")
        globalApplicationPool.define_metric("enabled", "enabled")

        localApplicationPool = definition.define_object_type("localApplicationPool", "Local application pool")
        localApplicationPool.define_string_identifier("uuid", "UUID")
        localApplicationPool.define_string_property("id", "id")
        localApplicationPool.define_string_property("name", "name")
        localApplicationPool.define_string_property("farm_id", "farm_id")
        localApplicationPool.define_string_property("type", "type")
        localApplicationPool.define_metric("enabled", "enabled")

        RDSFarm = definition.define_object_type("RDSFarm", "RDS Farm")
        RDSFarm.define_string_identifier("uuid", "UUID")
        RDSFarm.define_string_property("id", "id")
        RDSFarm.define_string_property("name", "name")
        RDSFarm.define_metric("enabled", "enabled")
        RDSFarm.define_string_property("type", "type")

        RDSHost = definition.define_object_type("RDSHost", "RDS Host")
        RDSHost.define_string_identifier("uuid", "UUID")
        RDSHost.define_string_property("id", "id")
        RDSHost.define_string_property("farm_id", "farm_id")
        RDSHost.define_string_property("name", "name")
        RDSHost.define_metric("enabled", "enabled")
        RDSHost.define_metric("session_count","session_count")
        RDSHost.define_metric("max_session_count", "max_session_count")
        RDSHost.define_metric("max_session_count_configured", "max_session_count_configured")
        RDSHost.define_metric("state", "state")
        
        localSession = definition.define_object_type("localSession", "Local session")
        localSession.define_string_identifier("uuid", "UUID")
        localSession.define_string_property("id", "id")
        localSession.define_string_property("name", "name")
        localSession.define_metric("enabled", "enabled")

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
                logger.info(f"token: {token}")
            else:
                logger.error("Error:", status_code)

            return result

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

            client = RestClient(base_url)
            status_code, response_data = client.post("/rest/login", headers, json_payload)

            if status_code == 200:
                token = response_data.get("access_token")
            else:
                logger.error("Error:", status_code)

            global_Desktop_Pools = get_global_desktop_pools(host, port, token, 1)
            global_Application_Pools = get_global_application_pools(host, port, token, 1)

            local_Pods = get_local_pod(host, port, token, global_Desktop_Pools, global_Application_Pools)
            local_Sites = get_local_site(host, port, token, local_Pods)
            local_Desktop_Pools = get_local_desktop_pools(host, port, token, 1, global_Desktop_Pools)
            
            rds_farms = get_rds_farms(host, port, token, 1 )
            
            local_Application_Pools = get_local_application_pools(host, port, token, 1, rds_farms, global_Application_Pools)
            rds_hosts = get_rds_hosts(host, port, token, 1, rds_farms)
            
            local_Sessions = get_local_sessions(host, port, token, 1, local_Desktop_Pools, rds_farms, rds_hosts)

            result.add_objects(global_Desktop_Pools)
            result.add_objects(global_Application_Pools)
            result.add_objects(local_Pods)
            result.add_objects(local_Sites)
            result.add_objects(local_Desktop_Pools)
            result.add_objects(local_Application_Pools)
            result.add_objects(rds_farms)
            result.add_objects(rds_hosts)
            result.add_objects(local_Sessions)

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            # TODO: If any connections are still open, make sure they are closed before returning
            logger.info(f"Returning collection result {result.get_json()}")
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
