import boto3  #biblioteca oficial de python para comunicarse con los servicios de AWS

#Base de datos dynamodb local
dynamodb= boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8002', #donde enviar las peticiones
    region_name='eu-south-2', 
    aws_access_key_id='local',
    aws_secret_access_key='local'    
)

try:
    dynamodb.create_table(
        TableName='Profiles',
        KeySchema= [    #clave primaria
            {
                'AttributeName' : 'user_id',
                'KeyType' : 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName' : 'user_id',
                'AttributeType' : 'S'   #tipo String
            }
        ],
        BillingMode= 'PAY_PER_REQUEST'  #Se adapta automáticamente a las peticiones de lectura-escritura (no pagamos porque es local)
    )

    print('Tabla Profiles creada correctamente')

except dynamodb.exceptions.ResourceInUseException:
    print('La tabla Profiles ya existe')