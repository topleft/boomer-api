import json


def handler(event, context):
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {'content': 'application/json'},
        "multiValueHeaders": {},
        'body': json.dumps({'message': 'Ok Boomer'})
    }
