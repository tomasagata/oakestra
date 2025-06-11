import json

from bson.objectid import ObjectId
from db import netservices_db
from flask.views import MethodView
from flask_smorest import Blueprint
from services.hook_service import pre_post_hook
from werkzeug import exceptions

netservicesblp = Blueprint("Network Services", "netservices", url_prefix="/api/v1/netservices")


@netservicesblp.route("/")
class AllNetServicesController(MethodView):
    @pre_post_hook("netservices")
    def post(self, data, *args, **kwargs):
        result = netservices_db.create_netservice(data)
        return json.dumps(result, default=str)


@netservicesblp.route("/<ns_id>")
class NetServiceController(MethodView):
    def get(self, query, **kwargs):
        ns_id = kwargs.get("ns_id")
        if ObjectId.is_valid(ns_id) is False:
            raise exceptions.BadRequest()

        netservice = netservices_db.find_netservice_by_id(ns_id)
        if netservice is None:
            raise exceptions.NotFound()

        return json.dumps(netservice, default=str)

    @pre_post_hook("netservices", with_param_id="ns_id")
    def delete(self, *args, **kwargs):
        ns_id = kwargs.get("ns_id")
        result = netservices_db.delete_ns(ns_id)

        return json.dumps(result, default=str)
