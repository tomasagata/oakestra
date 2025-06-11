
import io
import re
import yaml
from libraries.resource_abstractor_client.resource_abstractor_client import app_operations, cluster_operations, job_operations
from requests import post

def create_network_services_of_app(application):
    microservices = job_operations.get_jobs_of_application(application['applicationID'])
    net_service = application['net_service']
    
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
        net_service['application-functions'].append(af_details)
    
    # Resolve the cluster id based on its name
    cluster_name = net_service.get('cluster')
    if cluster_name is None: return {
        "message": "missing property 'cluster' on network service definition"
    }, 400
    cluster_data = cluster_operations.get_resource_by_name(cluster_name)

    if cluster_data is None: return {
        "message": f"unable to get cluster named '{cluster_name}'" 
    }, 404

    # Save the network service in the database
    ns_id = store_net_service(net_service)

    if ns_id is None: return {
        "message": f"unable to store network service in database" 
    }, 500

    net_service['id'] = ns_id
    return send_net_service_to_cluster(net_service, cluster_data)

def store_net_service(ns):
    net_service = create_netservice(ns)
    return net_service.get('_id')

def delete_net_service(net_service_id):
    net_service = get_netservice_by_id(net_service_id)
    if net_service is None: return {
        "message": f"network service not found" 
    }, 404

    cluster_data = cluster_operations.get_resource_by_name(net_service['cluster'])
    if cluster_data is None: return {
        "message": f"cluster not found" 
    }, 500

    response, status = delete_net_service_from_cluster(net_service, cluster_data)
    if status != 200: return response, status

    response = delete_netservice(net_service_id)
    if response is None: return None, 500
    return response, 200

def send_net_service_to_cluster(net_service, cluster_data):
    net_service_yaml = yaml.dump(net_service)

    file_obj = io.BytesIO(net_service_yaml.encode('utf-8'))
    file_obj.name = 'nsd.yml'  # Simulate a real file name

    # Send POST request with the file
    files = {'file': (file_obj.name, file_obj, 'application/x-yaml')}
    response = post(
        f"http://{cluster_data['cluster_ip']}:5000/iml/yaml/deploy/", 
        files=files
    )
    
    if response.status_code != 200: return {
        "message": f"error when sending network service descriptor to IML" 
    }
    return None, 200

def delete_net_service_from_cluster(net_service, cluster_data):
    net_service_yaml = yaml.dump(net_service)

    file_obj = io.BytesIO(net_service_yaml.encode('utf-8'))
    file_obj.name = 'nsd.yml'  # Simulate a real file name

    # Send POST request with the file
    files = {'file': (file_obj.name, file_obj, 'application/x-yaml')}
    response = post(
        f"http://{cluster_data['cluster_ip']}:5000/iml/yaml/deploy/", 
        files=files
    )
    
    if response.status_code != 200: return {
        "message": f"error when sending network service descriptor to IML" 
    }
    return None, 200


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