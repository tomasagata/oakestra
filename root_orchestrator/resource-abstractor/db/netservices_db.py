from datetime import datetime

import db.mongodb_client as db
from bson.objectid import ObjectId


def find_netservice(filter={}):
    return db.mongo_netservices.find(filter)


def find_netservice_by_id(ns_id, extra_filter={}):
    filter = {**extra_filter, "_id": ObjectId(ns_id)}
    ns = list(find_netservice(filter=filter))

    return ns[0] if ns else None


def delete_ns(ns_id):
    filter = {"_id": ObjectId(ns_id)}

    return db.mongo_netservices.find_one_and_delete(filter)


def update_netservice(ns_id, data):
    data.pop("_id", None)

    return db.mongo_netservices.find_one_and_update(
        {"_id": ObjectId(ns_id)},
        {"$set": data},
        return_document=True,
    )


def create_netservice(ns_id):
    inserted = db.mongo_netservices.insert_one(ns_id)

    return update_netservice(str(inserted.inserted_id), {"nsID": str(inserted.inserted_id)})