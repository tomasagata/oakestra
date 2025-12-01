from email.policy import default


ns_schema = {
    "type": ["object", "null"],
    "properties": {
        "nsID": {"type": "string"},
        "ns_name": {"type": "string", "default": ""},
        "ns_desc": {"type": "string", "default": ""},
        "cluster": {"type": "string"},
        "functions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "default": ""},
                    "function_namespace": {"type": "string", "default": "default"},
                    "type": {"type": "string", "default": "simple"},
                    "containers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "image": {"type": "string"},
                                "command": {"type": ["array", "null"], "items": {"type": "string"}},
                                "args": {"type": ["array", "null"], "items": {"type": "string"}},
                            },
                            "required": ["name", "image"],
                        },
                    },
                    "ns_ref": {"type": "string"},
                    "subfunctions": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "default": ""},
                                "id": {"type": "integer"},
                            },
                            "required": ["id"],
                        }
                    }
                },
                "required": ["function_name", "function_namespace", "containers", "ns_ref"],
            }
        },
        "service_chains": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chain_name": {"type": "string"},
                    "chain_namespace": {"type": "string", "default": "default"},
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "intermediate_functions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["chain_name", "from", "to"],
            }
        }
    },
    "required": ["cluster"],
}

sla_schema = {
    "type": "object",
    "properties": {
        "sla_version": {"type": "string"},
        "customerID": {"type": "string"},  # was integer
        "applications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "applicationID": {"type": "string"},  # was integer
                    "application_name": {"type": "string", "pattern": "^[a-zA-Z0-9]{1,30}$"},
                    "application_namespace": {"type": "string", "pattern": "^[a-zA-Z0-9]{1,30}$"},
                    "application_desc": {"type": "string"},
                    "microservices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "microserviceID": {
                                    "type": "string",
                                    "maxLength": 0,
                                },  # disabling this for now
                                "microservice_name": {
                                    "type": "string",
                                    "pattern": "^[a-zA-Z0-9]{1,30}$",
                                },
                                "microservice_namespace": {
                                    "type": "string",
                                    "pattern": "^[a-zA-Z0-9]{1,30}$",
                                },
                                "virtualization": {"type": "string"},
                                "memory": {"type": "integer"},
                                "vcpus": {"type": "integer"},
                                "vgpus": {"type": "integer"},
                                "vtpus": {"type": "integer"},
                                "bandwidth_in": {"type": "integer"},
                                "bandwidth_out": {"type": "integer"},
                                "storage": {"type": "integer"},
                                "code": {"type": "string"},
                                "state": {"type": "string"},
                                "port": {"type": "string"},
                                "ns_ref": {"type": "string"},
                                "one_shot": {"type": "boolean", "default": False},
                                "privileged": {"type": "boolean", "default": False},
                                "cmd": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "environment": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "sla_violation_strategy": {"type": "string"},
                                "target_node": {"type": "string"},
                                "addresses": {
                                    "type": "object",
                                    "properties": {
                                        "rr_ip": {"type": "string"},
                                        "rr_ip_v6": {"type": "string"},
                                        "closest_ip": {"type": "string"},
                                        "closest_ip_v6": {"type": "string"},
                                        "instances": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "from": {"type": "string"},
                                                    "to": {"type": "string"},
                                                    "start": {"type": "string"},
                                                },
                                            },
                                        },
                                    },
                                },
                                "added_files": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "args": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                    },
                                },
                                "constraints": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "area": {"type": "string"},
                                            "cluster": {"type": "string"},
                                            "node": {"type": "string"},
                                            "location": {"type": "string"},
                                            "threshold": {"type": "number"},
                                            "rigidness": {"type": "number"},
                                            "convergence_time": {"type": "integer"},
                                            "needs": {"type": "array", "items": {"type": "string"}},
                                            "allowed": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                        "required": ["type"],
                                    },
                                },
                                "connectivity": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "target_microservice_id": {
                                                "type": "string"
                                            },  # was integer
                                            "con_constraints": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "type": {"type": "string"},
                                                        "threshold": {"type": "number"},
                                                        "rigidness": {"type": "number"},
                                                        "convergence_time": {"type": "integer"},
                                                    },
                                                    "required": [
                                                        "type",
                                                        "threshold",
                                                        "rigidness",
                                                        "convergence_time",
                                                    ],
                                                },
                                            },
                                        },
                                        "required": [
                                            "target_microservice_id",
                                            "con_constraints",
                                        ],
                                    },
                                },
                            },
                            "required": [
                                "microservice_name",
                                "microservice_namespace",
                                "virtualization",
                                "code",
                            ],
                        },
                        "exclusiveMinimum": 0,
                    },
                    "net_service": ns_schema,
                },
                "required": [
                    "application_name",
                    "application_namespace",
                    "microservices",
                ],
            },
        },
        "args": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": ["sla_version", "customerID", "applications"],
}

sla_microservice_schema = sla_schema["properties"]["applications"]["items"]["properties"][
    "microservices"
]["items"]
sla_microservices_schema = sla_schema["properties"]["applications"]["items"]["properties"][
    "microservices"
]
