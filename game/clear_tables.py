
import boto3

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8004',
    region_name='eu-south-2',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

# Claves primarias de cada tabla
tables = {
    'Games': ['game_id'],
    'GameResponses': ['user_id', 'response_id']
}

for table_name, keys in tables.items():

    table = dynamodb.Table(table_name)

    # Recorrer todos los registros de la tabla
    response = table.scan(
        ProjectionExpression=', '.join(keys)
    )

    items = response['Items']

    # Borrar los registros encontrados
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    key: item[key]
                    for key in keys
                }
            )

    print(f'{table_name}: {len(items)} registros eliminados')
