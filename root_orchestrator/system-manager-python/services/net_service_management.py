
import logging
from flask import app
from resource_abstractor_client import app_operations, cluster_operations, job_operations
from requests import post

def create_network_services_of_app(user_id, application):
    app_id = application["applicationID"]
    net_service = application['net_service']
    nsd = dict()
    aliases = dict()

    # Get the microservices of the application
    microservices = job_operations.get_jobs_of_application(app_id)
    if microservices is None:
        return {
            "message": f"unable to get microservices for application {app_id}"
        }, 500

    # Obtain list of application functions from microservices by extracting `ns_ref` property
    nsd['application-functions'] = []
    for microservice in microservices:
        ns_ref = microservice.get('ns_ref')
        if not ns_ref: continue
        # if alias already exists, return error
        if aliases.get(ns_ref, None) is not None:
            return {
                "message": f"duplicate alias '{ns_ref}' found"
            }, 400
        af_details = {
            'id': microservice['microserviceID'],
            'name': microservice['microservice_name'],
            'namespace': microservice.get('microservice_namespace', 'default'),
        }
        aliases[ns_ref] = af_details
        nsd['application-functions'].append(af_details)
    
    network_functions = net_service.get('functions', [])
    nsd['network-functions'] = []
    for nf in network_functions:
        if nf.get('ns_ref') is None:
            return {
                "message": "missing property 'ns_ref' on network function definition"
            }, 400
        ns_ref = nf['ns_ref']
        if aliases.get(ns_ref) is not None:
            return {
                "message": f"duplicate alias '{ns_ref}' found"
            }, 400
        nf_details = {
            'name': nf['function_name'],
            'namespace': nf.get('function_namespace', 'default'),
            'image': nf.get('image', ''),
        }
        aliases[ns_ref] = nf_details
        nsd['network-functions'].append(nf_details)

    service_chains = net_service.get('service_chains', [])
    nsd['service-chains'] = []
    for sc in service_chains:
        if sc.get('chain_name') is None:
            return {
                "message": "missing property 'chain_name' on service chain definition"
            }, 400
        if sc.get('from') is None:
            return {
                "message": "missing property 'from' on service chain definition"
            }, 400
        if sc.get('to') is None:
            return {
                "message": "missing property 'to' on service chain definition"
            }, 400

        # Validate that all aliases used in the service chain are defined
        for alias in [sc['from'], sc['to']] + sc.get('intermediate_functions', []):
            if aliases.get(alias) is None:
                return {
                    "message": f"undefined alias '{alias}' used in service chain '{sc['chain_name']}'"
                }, 400

        from_af_details = aliases[sc['from']]
        to_af_details = aliases[sc['to']]
        intermediate_function_details = [{
            'name': aliases[alias]['name'],
            'namespace': aliases[alias]['namespace'],
        } for alias in sc.get('intermediate_functions', [])]

        sc_details = {
            'name': sc['chain_name'],
            'namespace': sc.get('chain_namespace', 'default'),
            'from': {
                'name': from_af_details['name'],
                'namespace': from_af_details['namespace'],
            },
            'to': {
                'name': to_af_details['name'],
                'namespace': to_af_details['namespace'],
            },
            'intermediate_functions': intermediate_function_details,
        }
        nsd['service-chains'].append(sc_details)

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
    ns_id = send_nsd_to_cluster(nsd, cluster_data)
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

def send_nsd_to_cluster(nsd, cluster_data):
    response = post(
        f"http://{cluster_data['ip']}:30050/api/v1/agent/nsd",
        json=nsd
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
        f"http://{cluster_data['ip']}:30050/api/v1/agent/nsd/{ns_id}"
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