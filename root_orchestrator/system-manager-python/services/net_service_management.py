
import io
import logging
import re
import yaml
from resource_abstractor_client import app_operations, cluster_operations, job_operations
from requests import post

def create_network_services_of_app(application):
    logging.debug(f"Creating network service for application {application['applicationID']}")
    microservices = job_operations.get_jobs_of_application(application['applicationID'])
    net_service = application['net_service']
    logging.debug(f"Network service definition: {net_service}")
    
    # Obtain list of application functions from microservices by extracting `ns_ref` property
    net_service['application-functions'] = []
    for microservice in microservices:
        ns_ref = microservice.get('ns_ref')
        if not ns_ref: continue
        af_details = {
            'id': microservice['microserviceID'],
            'instance-id': ns_ref,
            'af-version': '1.0'
        }
        logging.debug(f"Adding application function details: {af_details}")
        net_service['application-functions'].append(af_details)
    
    # Resolve the cluster id based on its name
    logging.debug(f"Resolving cluster for network service: {net_service.get('cluster')}")
    cluster_name = net_service.get('cluster')
    if cluster_name is None: 
        logging.error("Missing 'cluster' property in network service definition")
        return {
            "message": "missing property 'cluster' on network service definition"
        }, 400

    logging.debug(f"Getting cluster data for {cluster_name}")
    cluster_data = cluster_operations.get_resource_by_name(cluster_name)
    if cluster_data is None: 
        logging.error(f"Cluster {cluster_name} not found")
        return {
            "message": f"unable to get cluster named '{cluster_name}'" 
        }, 404

    # Save the network service in the database
    logging.debug(f"Storing network service in database")
    ns_id = store_net_service(net_service)
    if ns_id is None: 
        logging.error(f"Failed to store network service in database")
        return {
            "message": f"unable to store network service in database" 
        }, 500

    net_service['id'] = str(ns_id)
    return send_net_service_to_cluster(net_service, cluster_data)

def store_net_service(ns):
    net_service = create_netservice(ns)
    return net_service.get('_id')

def delete_net_service(net_service):
    ns_id = net_service.get('id')
    if ns_id is None: return {
        "message": f"network service not found" 
    }, 404

    ns_data = get_netservice_by_id(ns_id)
    if ns_data is None: return {
        "message": f"network service not found" 
    }, 404

    cluster_data = cluster_operations.get_resource_by_name(ns_data['cluster'])
    if cluster_data is None: return {
        "message": f"cluster not found" 
    }, 500

    response, status = delete_net_service_from_cluster(ns_id, cluster_data)
    if status != 200: return response, status

    response = delete_netservice(ns_id)
    if response is None: return None, 500
    return response, 200

def send_net_service_to_cluster(net_service, cluster_data):
    lnsd = {
        "lnsd": {
            "ns": net_service,
        } 
    }

    lnsd_yaml = yaml.dump(lnsd)

    file_obj = io.BytesIO(lnsd_yaml.encode('utf-8'))
    file_obj.name = 'nsd.yml'  # Simulate a real file name

    # Send POST request with the file
    files = {'file': (file_obj.name, file_obj, 'application/x-yaml')}
    response = post(
        f"http://{cluster_data['ip']}:30050/iml/yaml/deploy", 
        files=files
    )
    
    if response.status_code != 200: return {
        "message": f"error when sending network service descriptor to IML" 
    }, 500
    return None, 200

def delete_net_service_from_cluster(ns_id, cluster_data):

    # Send DELETE request with the network service ID
    response = delete(
        f"http://{cluster_data['ip']}:30050/iml/yaml/deploy/{ns_id}"
    )
    
    if not response.ok: return {
        "message": f"error when sending network service descriptor to IML" 
    }, 500

    return response.text, response.status_code


# =========== netservice_operations ===========

from requests import delete, get
from resource_abstractor_client.client_helper import make_request

NETSERVICES_API = "/api/v1/netservices"


def get_netservice_by_id(ns_id):
    request_address = f"{NETSERVICES_API}/{ns_id}"
    return make_request(get, request_address)


def create_netservice(data):
    return make_request(post, NETSERVICES_API, json=data)


def delete_netservice(ns_id):
    request_address = f"{NETSERVICES_API}/{ns_id}"
    return make_request(delete, request_address)