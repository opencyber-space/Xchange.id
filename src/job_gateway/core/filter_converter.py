from .task_registry_client import TasksRegistryClient
from .task_registry_listing_client import TasksDBRegistryClient

def query_translator(query):
    def translate_condition(condition):
        if "logicalOperator" in condition:
            return translate_logical_operator(condition)
        else:
            return translate_simple_condition(condition)

    def translate_simple_condition(condition):
        variable = condition["variable"]
        operator = condition["operator"]
        value = condition["value"]

        if operator == "LIKE":
            # MongoDB uses regex for LIKE operations
            regex_value = value.replace(".", r"\.").replace("*", ".*")
            return {variable: {"$regex": regex_value}}
        elif operator == "==":
            return {variable: value}
        elif operator == "IN":
            return {variable: {"$in": value}}
        elif operator == "<":
            return {variable: {"$lt": value}}
        elif operator == "<=":
            return {variable: {"$lte": value}}
        elif operator == ">":
            return {variable: {"$gt": value}}
        elif operator == ">=":
            return {variable: {"$gte": value}}
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def translate_logical_operator(condition):
        logical_operator = condition["logicalOperator"]
        sub_conditions = condition["conditions"]
        translated_conditions = [translate_condition(
            cond) for cond in sub_conditions]

        if logical_operator == "AND":
            return {"$and": translated_conditions}
        elif logical_operator == "OR":
            return {"$or": translated_conditions}
        else:
            raise ValueError(
                f"Unsupported logical operator: {logical_operator}")

    return translate_condition(query)
