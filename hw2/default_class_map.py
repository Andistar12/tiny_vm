"""
Contains the hardcoded method signatures of the primitive classes"
"""
default_class_map = {
    "Obj": {
        "superclass": "$",
        "field_list": {},
        "method_returns": {
            "$constructor": "Obj",
            "string": "String",
            "print": "Nothing"
        },
        "method_args": {
            "$constructor": [],
            "string": [],
            "print": []
        }
    },
    "Int": {
        "superclass": "Obj",
        "field_list": {},
        "method_returns": {
            "$constructor": "Int",
            "string": "String",
            "print": "Nothing",
            "plus": "Int",
            "minus": "Int",
            "times": "Int",
            "divide": "Int",
            "negate": "Int",
            "equals": "Boolean"
        },
        "method_args": {
            "$constructor": ["TODO"],
            "string": [],
            "print": [],
            "plus": ["Int"],
            "minus": ["Int"],
            "times": ["Int"],
            "divide": ["Int"],
            "negate": []
        }
    },
    "Boolean": {
        "superclass": "Obj",
        "field_list": {},
        "method_returns": {
            "$constructor": "Boolean",
            "string": "String",
            "print": "Nothing",
            "equals": "Boolean"
        },
        "method_args": {
            "$constructor": [],
            "string": [],
            "print": [],
            "equals": ["Obj"]
        }
    },
    "String": {
        "superclass": "Obj",
        "field_list": [],
        "method_returns": {
            "$constructor": "String",
            "string": "String",
            "print": "Nothing",
            "equals": "Boolean",
            "less": "Boolean",
            "plus": "String"
        },
        "method_args": {
            "$constructor": [],
            "string": [],
            "print": [],
            "equals": ["Obj"],
            "less": ["String"],
            "plus": ["String"]
        }
    }
}