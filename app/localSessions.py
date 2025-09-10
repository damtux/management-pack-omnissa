import aria.ops.adapter_logging as logging
import constants
import json
import math
from constants import ADAPTER_KIND
from aria.ops.object import Object
from typing import List
from aria.ops.data import Metric
from aria.ops.data import Property
from aria.ops.object import Identifier
from aria.ops.object import Key
from localDesktopPools import localDesktopPool
from RDSFarms import RDSFarm
from RDSHosts import RDSHost

from restcall import RestClient

logger = logging.getLogger(__name__)

class localSession(Object):
    def __init__(self, name, id):
        self.name = name
        self.id = id
        super().__init__(
            key=Key(
                name=name,
                adapter_kind=constants.ADAPTER_KIND,
                object_kind="localSession",
                identifiers=[Identifier(key="uuid", value=id)],
            )
        )

def get_local_sessions(host, port, token, page, localDesktopPools: List[localDesktopPool], RDSFarms: List[RDSFarm], RDSHosts: List[RDSHost]) -> List[localSession]:
        localSessions = []
        size = 1000 
        base_url = "https://" + str(host) + ":" + str(port)
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        client = RestClient(base_url)
        # Make a GET request to the device endpoint
        queryString = '/rest/inventory/v1/sessions?size=' + str(size) + '&page=' + str(page)
        status_code, response_data = client.get(queryString, headers)
        if status_code == 200:
            for obj in response_data:
                loginName = ''
                poolName = ''
                logonTime = 0
                farmName = ''
                machineName = ''
                rdsName = ''

                queryString = '/rest/external/v1/ad-users-or-groups/' + obj["user_id"]
                status_code, response_data2 = client.get(queryString, headers)
                if status_code == 200:
                    loginName = response_data2['login_name']

                if "desktop_pool_id" in obj and obj["desktop_pool_id"]:
                    queryString = '/rest/inventory/v1/desktop-pools/' + obj["desktop_pool_id"]
                    status_code, response_data3 = client.get(queryString, headers)
                    if status_code == 200:
                        poolName = response_data3['name']
                    # creating object and adding it to the result set

                if "farm_id" in obj and obj["farm_id"]:
                    queryString = '/rest/inventory/v1/farms/' + obj["farm_id"]
                    status_code, response_data4 = client.get(queryString, headers)
                    if status_code == 200:
                        farmName = response_data4['name']
                    # creating object and adding it to the result set    

                if "machine_id" in obj and obj["machine_id"]:
                    queryString = '/rest/inventory/v1/machines/' + obj["machine_id"]
                    status_code, response_data5 = client.get(queryString, headers)
                    if status_code == 200:
                        machineName = response_data5['name']
                    # creating object and adding it to the result set       

                if "rds_server_id" in obj and obj["rds_server_id"]:
                    queryString = '/rest/inventory/v1/rds_server_id/' + obj["rds_server_id"]
                    status_code, response_data6 = client.get(queryString, headers)
                    if status_code == 200:
                        rdsName = response_data6['name']
                    # creating object and adding it to the result set           
                
                if poolName:
                    sessionName = loginName + ":vdi:" + poolName
                if rdsName:
                    sessionName = loginName + ":rds:" + rdsName
                new_localSession = localSession(sessionName, obj["id"])
                new_localSession.with_property("id", obj["id"])

                if "desktop_pool_id" in obj and obj["desktop_pool_id"]:
                    for localPool in localDesktopPools:
                        if localPool.id == obj["desktop_pool_id"]:
                            new_localSession.add_parent(localPool)

                if "rds_server_id" in obj and obj["rds_server_id"]:
                    for RDSHost in RDSHosts:
                        if RDSHost.id == obj["rds_server_id"]:
                            new_localSession.add_parent(RDSHost)   

                if "farm_id" in obj and obj["farm_id"]:
                    for RDSFarm in RDSFarms:
                        if RDSFarm.id == obj["farm_id"]:
                            new_localSession.add_parent(RDSFarm)                   
                
                queryString = '/rest/helpdesk/v1/logon-timing/logon-segment?session_id=' + obj["id"]
                status_code, response_data7 = client.get(queryString, headers)
                if status_code == 200:
                    segment = json.loads(response_data7['logon_segment_data'])
                    if 'v1' in segment:
                        logonTime = math.ceil(segment['v1']['d']/1000)         
                
                new_localSession.with_property("state", obj["session_state"])
                new_localSession.with_property("type", obj["session_type"])
                new_localSession.with_property("version", obj["agent_version"])
                if "session_protocol" in obj:
                    new_localSession.with_property("protocol", obj["session_protocol"])
                new_localSession.with_property("pool", poolName)
                new_localSession.with_property("name",loginName)
                new_localSession.with_metric("LogonTime", logonTime)
                new_localSession.with_property("farmName", farmName)
                new_localSession.with_property("machineName", machineName)
                new_localSession.with_property("rdsName", rdsName)
                localSessions.append(new_localSession)
            if len(response_data) == size:
                get_local_sessions(host, port, token, page +1, localDesktopPools, RDSFarms, RDSHosts)
        else:
            logger.error("Error:", status_code)

        return localSessions

