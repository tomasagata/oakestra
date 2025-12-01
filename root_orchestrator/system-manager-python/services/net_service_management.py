from http import HTTPStatus
from resource_abstractor_client import app_operations, cluster_operations, job_operations
from requests import post

def create_network_services_of_app(user_id, application) -> tuple[dict, HTTPStatus]:
    app_id = application["applicationID"]
    net_service = application['net_service']

    # Get the microservices of the application
    microservices = job_operations.get_jobs_of_application(app_id)
    if microservices is None:
        return {
            "message": f"unable to get microservices for application {app_id}"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        nsd = create_nsd_from_net_service(net_service, microservices)
    except ValueError as e:
        return {
            "message": f"error when creating network service descriptor from network service definition: {str(e)}"
        }, HTTPStatus.BAD_REQUEST

    # Get the cluster name from the network service definition
    cluster_name = net_service.get('cluster')
    if cluster_name is None: 
        return {
            "message": "missing property 'cluster' on network service definition"
        }, HTTPStatus.BAD_REQUEST

    # Use the cluster name to get the cluster data
    cluster_data = cluster_operations.get_resource_by_name(cluster_name)
    if cluster_data is None: 
        return {
            "message": f"unable to get cluster named '{cluster_name}'" 
        }, HTTPStatus.NOT_FOUND
    
    # Send the network service descriptor to the cluster
    # The network service descriptor is a YAML file that contains the network service definition
    # The file is sent to the cluster using a POST request to the IML API
    # The IML API is running on port 30050 of the cluster
    try:
        send_nsd_to_cluster(nsd, cluster_data)
    except Exception as e:
        return {
            "message": f"error when sending network service descriptor to IML: {str(e)}"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    # Save the network service in the database
    json_response = app_operations.update_app(app_id, user_id, {
        "net_service": net_service
    })
    if json_response is None:
        return {
            "message": f"error when updating application with network service ID"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    return {"message": "Network service created successfully"}, HTTPStatus.OK

def delete_network_services_of_app(net_service, app_id) -> tuple[dict, HTTPStatus]:
    microservices = job_operations.get_jobs_of_application(app_id)
    if microservices is None: return {
        "message": f"unable to get microservices for application {app_id}"
    }, HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        nsd = create_nsd_from_net_service(net_service, microservices)
    except ValueError as e:
        return {
            "message": f"error when creating network service descriptor from network service definition: {str(e)}"
        }, HTTPStatus.BAD_REQUEST

    cluster_name = net_service.get('cluster')
    if cluster_name is None: return {
        "message": f"missing property 'cluster' on network service definition" 
    }, HTTPStatus.INTERNAL_SERVER_ERROR

    cluster_data = cluster_operations.get_resource_by_name(cluster_name)
    if cluster_data is None: return {
        "message": f"cluster not found" 
    }, HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        delete_net_service_from_cluster(nsd, cluster_data)
    except Exception as e:
        return {
            "message": f"error when deleting network service from IML: {str(e)}"
        }, HTTPStatus.INTERNAL_SERVER_ERROR
    
    return {"message": "Network service deleted successfully"}, HTTPStatus.OK

def send_nsd_to_cluster(nsd, cluster_data):
    response = post(
        f"http://{cluster_data['ip']}:30050/api/v1/agent/nsd/deploy",
        json=nsd
    )
    if not response.ok: 
        raise Exception(f"{response.text}")
    
    return response.text, response.status_code

def delete_net_service_from_cluster(nsd, cluster_data):
    # Send POST request with the network service descriptor to delete it
    response = post(
        f"http://{cluster_data['ip']}:30050/api/v1/agent/nsd/delete", 
        json=nsd
    )
    if not response.ok: 
        raise Exception(f"{response.text}")

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

# =========== nsd creation helpers ===========

def create_nsd_from_net_service(net_service, microservices):
    nsd = dict()
    aliases = dict()

    # Obtain list of application functions from microservices by extracting `ns_ref` property
    nsd['application-functions'] = []
    for microservice in microservices:
        af_details = {
            'id': microservice['microserviceID'],
            'name': microservice['microservice_name'],
            'namespace': microservice.get('microservice_namespace', 'default'),
        }
        nsd['application-functions'].append(af_details)

        ns_ref = microservice.get('ns_ref')
        if ns_ref is not None:
            # if alias already exists, return error
            if aliases.get(ns_ref) is not None:
                raise ValueError(f"duplicate alias '{ns_ref}' found")
            aliases[ns_ref] = af_details
    
    network_functions = net_service.get('functions', [])
    nsd['network-functions'] = []
    for nf in network_functions:
        try:
            name, namespace = parse_name_and_namespace(nf)
            ns_ref = parse_ns_ref(nf, aliases)
            type = parse_nf_type(nf)
            containers = parse_containers(nf)
            subfunctions = parse_nf_subfunctions(nf, type)
        except ValueError as e:
            raise ValueError(f"error processing network function '{ns_ref}': {str(e)}")
        nf_details = {
            'name': name,
            'namespace': namespace,
            'type': type,
            'containers': containers,
            'subFunctions': subfunctions,
        }
        aliases[ns_ref] = nf_details
        nsd['network-functions'].append(nf_details)

    service_chains = net_service.get('service_chains', [])
    nsd['service-chains'] = []
    for sc in service_chains:
        if sc.get('chain_name') is None:
            raise ValueError("missing property 'chain_name' on service chain definition")
        if sc.get('from') is None:
            raise ValueError("missing property 'from' on service chain definition")
        if sc.get('to') is None:
            raise ValueError("missing property 'to' on service chain definition")
        
        from_af_details = aliases.get(sc['from'])
        if from_af_details is None:
            raise ValueError(f"undefined alias '{sc['from']}' used in service chain '{sc['chain_name']}'")
        
        to_af_details = aliases.get(sc['to'])
        if to_af_details is None:
            raise ValueError(f"undefined alias '{sc['to']}' used in service chain '{sc['chain_name']}'")
        
        intermediate_function_details = []
        for alias in sc.get('intermediate_functions', []):
            try:
                nf_alias, subfunc_id = parse_nf_alias(alias)
                nf_details = aliases.get(nf_alias)
                if nf_details is None:
                    raise ValueError(f"undefined alias '{nf_alias}' used in service chain '{sc['chain_name']}'")    
                if nf_details['type'] == 'simple':
                    intermediate_function_details.append({
                        'name': nf_details['name'],
                        'namespace': nf_details['namespace'],
                    })
                    continue
                elif nf_details['type'] == 'multiplexed':
                    if subfunc_id is None:
                        raise ValueError(f"missing subfunction ID for multiplexed network function '{nf_alias}' in service chain '{sc['chain_name']}'")
                    subfunctions = nf_details.get('subFunctions', [])
                    subfunction_found = False
                    for subf in subfunctions:
                        if str(subf['id']) == str(subfunc_id):
                            intermediate_function_details.append({
                                'name': nf_details['name'],
                                'namespace': nf_details['namespace'],
                                'subFunctionID': subf['id']
                            })
                            subfunction_found = True
                            break
                    if not subfunction_found:
                        raise ValueError(f"subfunction ID '{subfunc_id}' not found in network function '{nf_alias}'")
                else:
                    raise ValueError(f"unknown network function type '{nf_details['type']}' for alias '{nf_alias}'")
            except ValueError as e:
                raise ValueError(f"error processing intermediate function alias '{alias}' in service chain '{sc['chain_name']}': {str(e)}")

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
            'functions': intermediate_function_details,
        }
        nsd['service-chains'].append(sc_details)
    
    return nsd

def parse_containers(nf_definition):
    containers_def = nf_definition.get('containers')
    if containers_def is None:
        raise ValueError("Containers definition is missing")
    if not isinstance(containers_def, list):
        raise ValueError("Containers definition must be a list")
    if containers_def == []:
        raise ValueError("Containers definition cannot be empty")
    containers = []
    for container in containers_def:
        if not isinstance(container, dict):
            raise ValueError("Each container definition must be a dictionary")
        if container.get('name') is None or container.get('image') is None:
            raise ValueError("Each container must have 'name' and 'image' properties")
        container_details = {
            'name': container.get('name', ''),
            'image': container.get('image', ''),
            'command': container.get('command', []),
            'args': container.get('args', []),
        }
        containers.append(container_details)
    return containers

def parse_nf_type(nf_definition):
    nf_type = nf_definition.get('type', 'simple')
    if nf_type not in ['simple', 'multiplexed']:
        raise ValueError(f"Invalid network function type '{nf_type}'")
    return nf_type

def parse_nf_subfunctions(nf_definition, nf_type):
    subfunctions_def = nf_definition.get('subfunctions', [])
    if not isinstance(subfunctions_def, list):
        raise ValueError("property 'subfunctions' must be a list")
    
    if nf_type == 'simple' and len(subfunctions_def) != 0:
        raise ValueError("property 'subfunctions' should not be defined for simple network function")
    elif nf_type == 'simple':
        return []
    
    subfunctions = []
    for subf_def in subfunctions_def:
        if subf_def.get('id') is None:
            raise ValueError("missing property 'id' on subfunction definition")
        subfunctions.append({
            'name': subf_def.get('name', ''),
            'id': subf_def['id'],
        })
    return subfunctions

def parse_ns_ref(nf_definition, aliases):
    ns_ref = nf_definition.get('ns_ref')
    if ns_ref is None:
        raise ValueError("Missing 'ns_ref' property")
    if aliases.get(ns_ref) is not None:
        raise ValueError(f"duplicate alias '{ns_ref}' found")
    return ns_ref

def parse_name_and_namespace(nf_definition):
    function_name = nf_definition.get('function_name')
    if function_name is None:
        raise ValueError("missing property 'function_name' on network function definition")
    function_namespace = nf_definition.get('function_namespace', 'default')
    return function_name, function_namespace

def parse_nf_alias(alias) -> tuple[str, int | None]:
    if not isinstance(alias, str):
        raise ValueError(f"unknown type of alias '{alias}'")
    nf_alias = alias
    subfunc_id = None
    if ':' in alias:
        splitted = alias.split(':')
        if len(splitted) != 2:
            raise ValueError(f"invalid intermediate function alias '{alias}'")
        nf_alias = splitted[0]
        subfunc_id = splitted[1]
    return nf_alias, subfunc_id