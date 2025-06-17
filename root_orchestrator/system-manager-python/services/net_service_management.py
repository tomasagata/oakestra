
import io
import logging
import re
from flask import app
import yaml
from resource_abstractor_client import app_operations, cluster_operations, job_operations
from requests import post

def create_network_services_of_app(user_id, application):
    app_id = application["applicationID"]
    net_service = application['net_service']

    # Get the microservices of the application
    microservices = job_operations.get_jobs_of_application(app_id)
    if microservices is None:
        return {
            "message": f"unable to get microservices for application {app_id}"
        }, 500

    # Obtain list of application functions from microservices by extracting `ns_ref` property
    net_service['application-functions'] = []
    for microservice in microservices:
        ns_ref = microservice.get('ns_ref')
        if not ns_ref: continue
        af_details = {
            'af-id': microservice['microserviceID'],
            'af-instance-id': ns_ref,
            'af-version': '1.0'
        }
        net_service['application-functions'].append(af_details)

    # Get the cluster name from the network service definition
    cluster_name = net_service.get('cluster')
    if cluster_name is None: 
        return {
            "message": "missing property 'cluster' on network service definition"
        }, 400

    # Use the cluster name to get the cluster data
    cluster_data = cluster_operations.get_resource_by_name(cluster_name)
    if cluster_data is None: 
        return {
            "message": f"unable to get cluster named '{cluster_name}'" 
        }, 404
    
    # Send the network service descriptor to the cluster
    # The network service descriptor is a YAML file that contains the network service definition
    # The file is sent to the cluster using a POST request to the IML API
    # The IML API is running on port 30050 of the cluster
    ns_id = send_net_service_to_cluster(net_service, cluster_data)
    if ns_id is None:
        return {
            "message": f"error when sending network service descriptor to IML"
        }, 500

    # Save the network service in the database
    json_response = app_operations.update_app(app_id, user_id, {
        "net_service": {
            "nsID": ns_id, 
            "cluster": cluster_name
        }
    })
    if json_response is None:
        return {
            "message": f"error when updating application with network service ID"
        }, 500

    return None, 200

def delete_net_service(net_service):
    ns_id = net_service.get('nsID')
    if ns_id is None: return {
        "message": f"missing property 'nsID' on network service definition" 
    }, 500

    cluster_name = net_service.get('cluster')
    if cluster_name is None: return {
        "message": f"missing property 'cluster' on network service definition" 
    }, 500

    cluster_data = cluster_operations.get_resource_by_name(cluster_name)
    if cluster_data is None: return {
        "message": f"cluster not found" 
    }, 500

    return delete_net_service_from_cluster(ns_id, cluster_data)

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
    if not response.ok: 
        return None

    # Extract the network service ID from the response
    try:
        response_data = response.json()
        ns_id = response_data.get('id')
        if not ns_id:
            logging.error("Network service ID not found in response")
            return None
    except ValueError:
        logging.error("Invalid JSON response from IML")
        return None
    
    return ns_id

def delete_net_service_from_cluster(ns_id, cluster_data):

    # Send DELETE request with the network service ID
    response = delete(
        f"http://{cluster_data['ip']}:30050/iml/yaml/deploy/{ns_id}"
    )
    
    if not response.ok: return {
        "message": f"error when sending network service descriptor to IML" 
    }, response.status_code

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